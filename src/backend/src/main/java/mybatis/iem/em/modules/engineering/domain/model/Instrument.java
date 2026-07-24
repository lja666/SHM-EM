package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class Instrument {
    private Long id;
    private Long projectId;
    private Long stationId;
    private String instrumentCode;
    private String instrumentName;
    private String instrumentType;
    private String vendor;
    private String model;
    private String serialNo;
    private String dtuCode;
    private String moduleNo;
    private String moduleName;
    private String channelNo;
    private String samplingMode;
    private BigDecimal samplingFrequency;
    private String rawUnitDesc;
    private String communicationMode;
    private String protocolCode;
    private String installLocation;
    private LocalDateTime installationTime;
    private String calibrationJson;
    private LocalDateTime installTime;
    private String status;
    private String connectionJson;
    private String metadataJson;
    private Integer enabled;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}





