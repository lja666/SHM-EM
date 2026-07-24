package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class Evidence {
    private Long id;
    private Long projectId;
    private Long eventId;
    private Long stationId;
    private String evidenceCode;
    private String evidenceType;
    private String resourceType;
    private String resourceUrl;
    private String relatedEventCode;
    private String sourceRecordKey;
    private String hashValue;
    private String metadataJson;
    private String linkType;
    private String confidence;
    private LocalDateTime archivedAt;
    private LocalDateTime capturedAt;
    private LocalDateTime createdAt;
    private String status;
}
