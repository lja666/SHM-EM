package mybatis.iem.em.modules.engineering.domain.model;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class PredictionBatchDetail {
    private PredictionBatch batch;
    private List<PredictionRun> runs = new ArrayList<PredictionRun>();
    private PredictionCompleteness completeness;
    private Integer linkedEventCount;
}
