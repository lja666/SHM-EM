package mybatis.iem.em.modules.engineering.application.dto;

import lombok.Data;
import com.fasterxml.jackson.annotation.JsonFormat;
import org.springframework.format.annotation.DateTimeFormat;

import java.time.LocalDateTime;
import java.util.List;

@Data
public class PredictionQuery {
    private String valueMode;
    private Long projectId;
    private String modelCode;
    private String targetType;
    private String featureCode;
    private String batchCode;
    private Long batchId;
    private Long runId;
    private Long stationId;
    private List<Long> stationIds;
    private Long instrumentId;
    private List<Long> instrumentIds;
    private String instrumentType;
    private String metricCode;
    private String registryCode;
    private String status;
    private Integer maxHorizonMinutes;
    private String qualityFilter;
    private Boolean includeObserved;
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime startTime;
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime endTime;
    private Integer limit;
}
