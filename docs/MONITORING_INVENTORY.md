# Monitoring Inventory Semantics

SHM-EM separates field monitoring points from the internal records used to
attach sensors, metrics, and observations. These counts must not be used
interchangeably.

| Inventory concept | Count | Meaning |
|---|---:|---|
| Numbered field monitoring points | 9 | Physical locations numbered 1 through 9 on the conceptual project plan |
| Sensor records | 74 | Unique sensor identifiers registered in `em_instrument` |
| Acquisition modules | 17 | Unique acquisition-module identifiers associated with the sensor records |
| DTUs | 6 | Unique data-transfer units associated with the sensor records |
| Internal station records | 73 | Installation-position rows in `em_station`; these are not field-point records |

The restricted source register contains 75 device rows across two acquisition
box workbooks. One sensor is listed in both workbooks, so identifier-based
deduplication produces 74 unique sensor records. The released database matches
all 74 unique identifiers in the restricted register.

## Sensor Type Breakdown

| Sensor type | Count |
|---|---:|
| Omnidirectional displacement gauge | 42 |
| Earth-pressure cell | 14 |
| Inclined static-level gauge | 10 |
| Differential-pressure water-level gauge | 6 |
| Triaxial accelerometer | 2 |
| **Total** | **74** |

The six water-level records contain two excavation gauges and four laboratory
gauges. The laboratory gauges are retained as observation sources but are not
prediction targets. Static-level reference locations and laboratory gauges do
not increase the numbered field-point count.

## API Contract

- `siteCount` and the compatibility field `stationCount` report the declared
  field monitoring-point count: 9.
- `stationRecordCount` reports the 73 internal installation-position rows for
  diagnostics only.
- `instrumentCount` reports 74 unique sensor records.
- `acquisitionModuleCount` and `dtuCount` report 17 and 6 respectively.

The authoritative field-point count is stored as `monitoringPointCount` in the
project spatial context. Database row counts are not used as a substitute for
this business concept.
