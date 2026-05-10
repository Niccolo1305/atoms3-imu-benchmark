# MPU6886 Static Bench Firmware

Firmware separato per caratterizzazione statica del solo MPU6886 su M5Stack AtomS3.
Non riusa la pipeline veicolo: niente ESKF, Madgwick, ZARU/ZUPT, GPS, MQTT, EMA,
rotazioni assi, calibrazioni ellissoidali, bias subtraction o compensazioni termiche.
Questa variante applica solo il DLPF hardware del MPU6886 a circa 20 Hz.

## Build e flash

```powershell
cd firmware\mpu6886-static-bench
pio run -e atoms3_mpu6886_static_bench
pio run -e atoms3_mpu6886_static_bench -t upload
pio device monitor -b 115200
```

## Hardware usato

- Board: M5Stack AtomS3
- Sensore: MPU6886, I2C address `0x68`
- I2C interno AtomS3: SDA `38`, SCL `39`, `400 kHz`
- microSD SPI: SCK `7`, MISO `8`, MOSI `6`, CS `5`, `25 MHz`

## Configurazione MPU6886

Il datasheet non espone una modalita FIFO "truly unfiltered" a basso rate
compatibile con un logger robusto via I2C+SD. Il bypass DLPF porta il gyro a
rate/banda molto alti (`FCHOICE_B != 00`, tabella CONFIG: fino a 32 kHz) e
l'accelerometro a 4 kHz (`ACCEL_FCHOICE_B=1`), quindi non e una scelta adatta
a FIFO 1 kB + bus I2C + logging SD.

Modalita implementata con LPF hardware a circa 20 Hz:

- `PWR_MGMT_1 (0x6B) = 0x01`: awake, clock PLL
- `PWR_MGMT_2 (0x6C) = 0x00`: accel e gyro XYZ attivi
- `SMPLRT_DIV (0x19) = 0x00`: FIFO/data output a `1 kHz`
- `CONFIG (0x1A) = 0x44`: FIFO stop-on-full, gyro `DLPF_CFG=4`
  - gyro 3 dB bandwidth circa `20 Hz`, noise bandwidth circa `30.5 Hz`, rate `1 kHz`
  - temperatura DLPF circa `20 Hz` secondo tabella CONFIG del datasheet
- `GYRO_CONFIG (0x1B) = 0x18`: `+-2000 dps`, `FCHOICE_B=00`
- `ACCEL_CONFIG (0x1C) = 0x10`: `+-8 g`
- `ACCEL_CONFIG2 (0x1D) = 0x04`: accel DLPF circa `21.2 Hz`, noise bandwidth circa `31.0 Hz`, rate `1 kHz`
- `INT_ENABLE (0x38) = 0x10`: abilita flag FIFO overflow
- `USER_CTRL (0x6A) = 0x40`: FIFO enable
- `FIFO_EN (0x23) = 0x18`: accel + temp + gyro in FIFO

Frame FIFO da 14 byte, ordine datasheet quando accel e gyro sono entrambi
abilitati:

```text
ACCEL_X, ACCEL_Y, ACCEL_Z, TEMP, GYRO_X, GYRO_Y, GYRO_Z
```

Il task IMU gira a 50 Hz, drena tutti i frame FIFO disponibili e scrive nel
record il frame piu recente. I frame precedenti sono scartati per decimazione;
non vengono mediati e non viene applicato nessun LPF software.

## Formato file

Ogni file e chiamato `MPU6886_###.BIN` sulla microSD.

- Header fisso: `256 byte`
- Record fisso: `256 byte`
- Header magic: `MPU6886B`
- Record magic: `0x4236384D`
- Endianness: little-endian, marker `0x1234`
- CRC: CRC16-CCITT init `0xFFFF`, poly `0x1021`, calcolato su ogni header/record
  esclusi gli ultimi 2 byte del CRC stesso

Campi diagnostici principali per record:

- `seq`
- `timestamp_us` da `esp_timer_get_time()`
- `fifo_count_before`, `fifo_count_after`
- `fifo_overrun` e `fifo_overrun_count`
- `fifo_frames_drained`
- `decimation_counter`
- `sample_fresh`
- `read_error_count`
- `sd_queue_high_watermark`
- `sd_records_written`
- `sd_records_dropped`
- `sd_partial_write_count`
- `sd_stall_count`
- `sd_reopen_count`
- `sd_flush_worst_us`
- `crc16`

Scale fisiche nel converter:

- accelerometro `+-8 g`: `4096 LSB/g`
- giroscopio `+-2000 dps`: `16.384 LSB/dps`
- temperatura: `TEMP_OUT / 326.8 + 25 degC`

## Scrittura SD

Il task SD riceve record da una queue e scrive sempre il record corrente con
offset byte esplicito:

```text
offset = 0
while offset < sizeof(record):
    written = File.write(record + offset, remaining)
    if written > 0: offset += written
    if written == 0: close/reopen, poi continua dallo stesso offset
```

Questa logica evita frammenti duplicati: un record parzialmente accettato dal
filesystem non viene mai riscritto dall'inizio.

Flush ogni `250` record, cioe circa `5 s` a 50 Hz.

## Conversione e validazione

```powershell
cd firmware\mpu6886-static-bench
python .\tools\mpu6886_static_convert.py E:\MPU6886_000.BIN --csv .\MPU6886_000.csv --summary-json .\MPU6886_000_summary.json
```

Validazione senza CSV:

```powershell
python .\tools\mpu6886_static_convert.py E:\MPU6886_000.BIN --no-csv
```

Il converter verifica:

- magic/header
- CRC header
- `record_size`
- `(file_size - header_size) % record_size`
- CRC per record
- continuita `seq`
- monotonia timestamp
- byte spuri/resync
- stima drop da gap `seq`
- stima drop/jitter da gap timestamp
- diagnostica finale SD/FIFO

Exit code `0` indica validazione pulita. Exit code `2` indica almeno un errore
strutturale o temporale.

## Protocollo test statico consigliato

1. Formattare microSD in FAT32/exFAT con cluster grandi se possibile.
2. Inserire la microSD prima del boot.
3. Fissare AtomS3 su supporto rigido, lontano da vibrazioni, cavi in trazione e
   flussi d'aria diretti.
4. Lasciare stabilizzare termicamente la scheda per almeno 10-15 minuti se si
   vuole misurare stabilita a temperatura costante.
5. Avviare il firmware e non toccare il banco durante il run.
6. Per Allan/bias instability/random walk: acquisire almeno 2 ore.
7. A fine test togliere alimentazione solo dopo alcuni secondi dall'ultimo stato
   seriale, cosi l'ultimo flush periodico ha alta probabilita di essere passato.
8. Convertire e controllare che:
   - `payload_mod_record_size == 0`
   - `records_crc_bad == 0`
   - `resync_count == 0`
   - `seq_gaps == 0`
   - `timestamp_nonmonotonic == 0`
   - `sd_records_dropped_final == 0`
   - `fifo_overrun_counter_final == 0`
