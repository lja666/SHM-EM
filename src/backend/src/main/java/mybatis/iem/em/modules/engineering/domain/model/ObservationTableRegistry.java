package mybatis.iem.em.modules.engineering.domain.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class ObservationTableRegistry {
    private Long id;
    private String registryCode;
    private Long projectId;
    private String instrumentType;
    private Long instrumentId;
    private String metricGroup;
    private String storageBackend;
    private String storageMode;
    private String logicalSeriesName;
    @JsonIgnore
    private String physicalTableName;
    private String schemaVersion;
    private BigDecimal sampleFrequencyHz;
    private String timePrecision;
    private Integer isQueryable;
    private Integer isEventSource;
    private String partitionStrategy;
    private String retentionPolicy;
    private String downsamplePolicy;
    private String accessPolicyJson;
    private String fieldMappingJson;
    private Integer enabled;
    private String remark;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}





