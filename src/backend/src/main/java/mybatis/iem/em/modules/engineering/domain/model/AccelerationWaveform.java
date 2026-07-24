package mybatis.iem.em.modules.engineering.domain.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import java.time.LocalDateTime;

@Data
public class AccelerationWaveform {
    private Long id;
    private Long projectId;
    private Long stationId;
    private Long instrumentId;
    private Long batchId;
    private Integer sampleIndex;
    private Integer sampleOffsetMs;
    private LocalDateTime sampleTime;
    private Integer xRaw;
    private Integer yRaw;
    private Integer zRaw;
    @JsonProperty("xAccel")
    private Double xAccel;
    @JsonProperty("yAccel")
    private Double yAccel;
    @JsonProperty("zAccel")
    private Double zAccel;
    private String accelUnit;
    private String qualityFlag;
    private String sourceRecordKey;
    private LocalDateTime createdAt;
}





