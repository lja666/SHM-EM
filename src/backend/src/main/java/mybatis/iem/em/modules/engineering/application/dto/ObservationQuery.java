package mybatis.iem.em.modules.engineering.application.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;
import org.springframework.format.annotation.DateTimeFormat;

import java.time.LocalDateTime;
import java.util.List;

@Data
public class ObservationQuery {
    private String registryCode;
    private Long projectId;
    private Long stationId;
    private List<Long> stationIds;
    private Long instrumentId;
    private List<Long> instrumentIds;
    private String instrumentType;
    private String sensorNo;
    private String metricCode;
    private Long batchId;
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime startTime;
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime endTime;
    private Integer limit = 200;
}





