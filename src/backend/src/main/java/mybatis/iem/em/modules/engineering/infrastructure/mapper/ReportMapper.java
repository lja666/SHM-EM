package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import mybatis.iem.em.modules.engineering.domain.model.Report;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface ReportMapper {
    List<Report> selectReports(@Param("projectId") Long projectId, @Param("limit") Integer limit);

    Report selectById(@Param("id") Long id);

    int updateGeneratedFile(@Param("id") Long id,
                            @Param("format") String format,
                            @Param("downloadUrl") String downloadUrl,
                            @Param("hash") String hash,
                            @Param("generatedAt") LocalDateTime generatedAt);

    int upsertReportEvidence(@Param("reportId") Long reportId);

    int linkReportEvidence(@Param("reportId") Long reportId);
}
