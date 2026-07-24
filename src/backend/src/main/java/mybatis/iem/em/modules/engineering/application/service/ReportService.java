package mybatis.iem.em.modules.engineering.application.service;

import mybatis.iem.em.modules.engineering.domain.model.Report;

import java.io.IOException;
import java.nio.file.Path;
import java.util.List;

public interface ReportService {
    List<Report> list(Long projectId, Integer limit);

    Path reportFile(Long id, String format) throws IOException;

    String reportFileName(Long id, String format);
}
