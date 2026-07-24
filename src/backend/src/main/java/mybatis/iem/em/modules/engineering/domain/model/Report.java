package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class Report {
    private Long id;
    private Long projectId;
    private Long eventId;
    private Long templateId;
    private String reportName;
    private String reportTitle;
    private String reportType;
    private String contentHtml;
    private String contentText;
    private String docxUrl;
    private String pdfUrl;
    private String reportUrl;
    private String reportHash;
    private String metadataJson;
    private LocalDateTime generatedAt;
    private String status;
}
