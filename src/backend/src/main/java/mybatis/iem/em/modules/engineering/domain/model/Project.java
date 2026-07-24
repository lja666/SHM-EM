package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class Project {
    private Long id;
    private String projectCode;
    private String projectName;
    private String infrastructureType;
    private String scenarioLabel;
    private String locationText;
    private BigDecimal longitude;
    private BigDecimal latitude;
    private String coordinateSystem;
    private String coordinateSource;
    private String coordinateQuality;
    private String mapProvider;
    private String description;
    private String spatialContextJson;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private String status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}





