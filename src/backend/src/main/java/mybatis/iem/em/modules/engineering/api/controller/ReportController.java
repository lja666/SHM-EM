package mybatis.iem.em.modules.engineering.api.controller;

import mybatis.iem.em.common.ApiResponse;
import mybatis.iem.em.modules.engineering.application.service.ReportService;
import mybatis.iem.em.modules.engineering.domain.model.Report;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.List;

@RestController
@RequestMapping("/api/em/reports")
public class ReportController {
    private final ReportService service;

    public ReportController(ReportService service) {
        this.service = service;
    }

    @GetMapping
    public ApiResponse<List<Report>> list(@RequestParam(required = false) Long projectId,
                                           @RequestParam(required = false) Integer limit) {
        return ApiResponse.ok(service.list(projectId, limit));
    }

    @GetMapping("/{id}/download")
    public ResponseEntity<Resource> download(@PathVariable Long id,
                                             @RequestParam(defaultValue = "pdf") String format) throws IOException {
        Path file = service.reportFile(id, format);
        String normalizedFormat = "docx".equalsIgnoreCase(format) ? "docx" : "pdf";
        MediaType mediaType = "docx".equals(normalizedFormat)
            ? MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            : MediaType.APPLICATION_PDF;
        ContentDisposition disposition = ContentDisposition.attachment()
            .filename(service.reportFileName(id, normalizedFormat), StandardCharsets.UTF_8)
            .build();
        return ResponseEntity.ok()
            .contentType(mediaType)
            .header(HttpHeaders.CONTENT_DISPOSITION, disposition.toString())
            .body(new FileSystemResource(file));
    }
}
