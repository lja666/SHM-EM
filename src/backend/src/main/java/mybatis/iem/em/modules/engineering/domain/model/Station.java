package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class Station {
    private Long id;
    private Long projectId;
    private String stationCode;
    private String stationName;
    private String stationType;
    private String positionDesc;
    private BigDecimal longitude;
    private BigDecimal latitude;
    private BigDecimal x;
    private BigDecimal y;
    private BigDecimal z;
    private BigDecimal layoutX;
    private BigDecimal layoutY;
    private BigDecimal elevation;
    private LocalDateTime installationTime;
    private String status;
    private String spatialContextJson;
    private String metadataJson;
    private Integer enabled;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}





