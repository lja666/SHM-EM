package mybatis.iem.em.modules.engineering.application.service.impl;

import com.lowagie.text.Document;
import com.lowagie.text.Element;
import com.lowagie.text.Font;
import com.lowagie.text.PageSize;
import com.lowagie.text.Paragraph;
import com.lowagie.text.pdf.BaseFont;
import com.lowagie.text.pdf.PdfWriter;
import mybatis.iem.em.common.BusinessException;
import mybatis.iem.em.modules.engineering.application.service.ReportService;
import mybatis.iem.em.modules.engineering.domain.model.Report;
import mybatis.iem.em.modules.engineering.infrastructure.mapper.ReportMapper;
import org.apache.poi.xwpf.usermodel.ParagraphAlignment;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFRun;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

@Service
public class ReportServiceImpl implements ReportService {
    private static final DateTimeFormatter TIME_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private final ReportMapper mapper;
    private final Path reportStorageRoot;

    public ReportServiceImpl(ReportMapper mapper,
                             @Value("${report.storage-root:${user.dir}/report-files}") String reportStorageRoot) {
        this.mapper = mapper;
        this.reportStorageRoot = Paths.get(reportStorageRoot).toAbsolutePath().normalize();
    }

    @Override
    public List<Report> list(Long projectId, Integer limit) {
        List<Report> reports = mapper.selectReports(projectId, normalizeLimit(limit));
        return reports == null ? Collections.emptyList() : reports;
    }

    @Override
    public Path reportFile(Long id, String format) throws IOException {
        Report report = findReport(id);
        String normalizedFormat = normalizeFormat(format);
        Files.createDirectories(reportStorageRoot);
        Path file = reportStorageRoot.resolve("report-" + report.getId() + "." + normalizedFormat).normalize();
        if (!file.startsWith(reportStorageRoot)) {
            throw new IOException("Invalid report path");
        }
        if (!Files.exists(file) || Files.size(file) == 0) {
            if ("docx".equals(normalizedFormat)) {
                writeDocx(report, file);
            } else {
                writePdf(report, file);
            }
            String downloadUrl = "/api/em/reports/" + report.getId() + "/download?format=" + normalizedFormat;
            mapper.updateGeneratedFile(report.getId(), normalizedFormat, downloadUrl, sha256(file), LocalDateTime.now());
            mapper.upsertReportEvidence(report.getId());
            mapper.linkReportEvidence(report.getId());
        }
        return file;
    }

    @Override
    public String reportFileName(Long id, String format) {
        Report report = findReport(id);
        String normalizedFormat = normalizeFormat(format);
        String title = firstText(report.getReportTitle(), report.getReportName(), "Monitoring report");
        return safeFileName(title) + "-" + report.getId() + "." + normalizedFormat;
    }

    private int normalizeLimit(Integer limit) {
        if (limit == null || limit <= 0) {
            return 100;
        }
        return Math.min(limit, 1000);
    }

    private Report findReport(Long id) {
        if (id == null) {
            throw new BusinessException("report id is required");
        }
        Report report = mapper.selectById(id);
        if (report == null) {
            throw new BusinessException("report is not found: " + id);
        }
        return report;
    }

    private String normalizeFormat(String format) {
        String value = format == null ? "pdf" : format.toLowerCase(Locale.ROOT);
        return "docx".equals(value) ? "docx" : "pdf";
    }

    private void writeDocx(Report report, Path file) throws IOException {
        try (XWPFDocument document = new XWPFDocument(); OutputStream outputStream = Files.newOutputStream(file)) {
            XWPFParagraph titleParagraph = document.createParagraph();
            titleParagraph.setAlignment(ParagraphAlignment.CENTER);
            XWPFRun titleRun = titleParagraph.createRun();
            titleRun.setBold(true);
            titleRun.setFontFamily("Arial");
            titleRun.setFontSize(18);
            titleRun.setText(firstText(report.getReportTitle(), report.getReportName(), "SHM-EM Event Report"));

            for (String line : reportBodyLines(report)) {
                addDocxParagraph(document, line, false);
            }
            document.write(outputStream);
        }
    }

    private void addDocxParagraph(XWPFDocument document, String text, boolean bold) {
        XWPFParagraph paragraph = document.createParagraph();
        XWPFRun run = paragraph.createRun();
        run.setFontFamily("Arial");
        run.setFontSize(11);
        run.setBold(bold);
        run.setText(text);
    }

    private void writePdf(Report report, Path file) throws IOException {
        Document document = new Document(PageSize.A4, 36, 36, 36, 36);
        try (OutputStream outputStream = Files.newOutputStream(file)) {
            PdfWriter.getInstance(document, outputStream);
            document.open();
            Font titleFont = pdfFont(18, Font.BOLD);
            Font normalFont = pdfFont(10, Font.NORMAL);

            Paragraph title = new Paragraph(firstText(report.getReportTitle(), report.getReportName(), "SHM-EM Event Report"), titleFont);
            title.setAlignment(Element.ALIGN_CENTER);
            title.setSpacingAfter(16);
            document.add(title);
            for (String line : reportBodyLines(report)) {
                document.add(new Paragraph(line, normalFont));
            }
        } finally {
            document.close();
        }
    }

    private List<String> reportBodyLines(Report report) {
        List<String> lines = new ArrayList<String>();
        lines.add("Project ID: " + nullSafe(report.getProjectId()) + "; Event ID: " + nullSafe(report.getEventId()));
        lines.add("Report type: " + nullSafe(report.getReportType()) + "; Status: " + nullSafe(report.getStatus()));
        lines.add("Generated at: " + (report.getGeneratedAt() == null ? "not generated" : TIME_FORMATTER.format(report.getGeneratedAt())));
        String body = firstText(report.getContentText(), stripHtml(report.getContentHtml()), "This report instance has no body content.");
        for (String line : body.split("\\r?\\n")) {
            if (StringUtils.hasText(line)) {
                lines.add("Body: " + line.trim());
            }
        }
        if (StringUtils.hasText(report.getMetadataJson())) {
            lines.add("Metadata: " + report.getMetadataJson());
        }
        if (StringUtils.hasText(report.getReportHash())) {
            lines.add("Registered hash: " + report.getReportHash());
        }
        return lines;
    }

    private Font pdfFont(int size, int style) {
        try {
            String simsun = "C:/Windows/Fonts/simsun.ttc,0";
            if (Files.exists(Paths.get("C:/Windows/Fonts/msyh.ttc"))) {
                simsun = "C:/Windows/Fonts/msyh.ttc,0";
            }
            BaseFont baseFont = BaseFont.createFont(simsun, BaseFont.IDENTITY_H, BaseFont.EMBEDDED);
            return new Font(baseFont, size, style);
        } catch (Exception ignored) {
            return new Font(Font.HELVETICA, size, style);
        }
    }

    private String sha256(Path file) throws IOException {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (InputStream inputStream = Files.newInputStream(file)) {
                byte[] buffer = new byte[8192];
                int read;
                while ((read = inputStream.read(buffer)) >= 0) {
                    digest.update(buffer, 0, read);
                }
            }
            StringBuilder builder = new StringBuilder();
            for (byte b : digest.digest()) {
                builder.append(String.format("%02x", b));
            }
            return builder.toString();
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is not available", ex);
        }
    }

    private String stripHtml(String value) {
        if (!StringUtils.hasText(value)) {
            return null;
        }
        return value.replaceAll("<[^>]+>", " ").replaceAll("\\s+", " ").trim();
    }

    private String firstText(String... values) {
        for (String value : values) {
            if (StringUtils.hasText(value)) {
                return value.trim();
            }
        }
        return "";
    }

    private String nullSafe(Object value) {
        return value == null ? "-" : String.valueOf(value);
    }

    private String safeFileName(String value) {
        return value.replaceAll("[\\\\/:*?\"<>|\\s]+", "_");
    }
}
