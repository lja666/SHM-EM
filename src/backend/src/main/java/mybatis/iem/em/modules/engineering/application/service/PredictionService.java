package mybatis.iem.em.modules.engineering.application.service;

import mybatis.iem.em.modules.engineering.application.dto.PredictionQuery;
import mybatis.iem.em.modules.engineering.domain.model.PredictionBatch;
import mybatis.iem.em.modules.engineering.domain.model.PredictionDisplay;
import mybatis.iem.em.modules.engineering.domain.model.PredictionFeatureMapping;
import mybatis.iem.em.modules.engineering.domain.model.PredictionModel;
import mybatis.iem.em.modules.engineering.domain.model.PredictionBatchDetail;
import mybatis.iem.em.modules.engineering.domain.model.PredictionCompleteness;
import mybatis.iem.em.modules.engineering.domain.model.PredictionRun;
import mybatis.iem.em.modules.engineering.domain.model.MetricSeriesPoint;
import mybatis.iem.em.modules.engineering.domain.model.EventPredictionTrace;

import java.util.List;

public interface PredictionService {
    List<PredictionBatch> batches(PredictionQuery query);

    List<PredictionModel> models(PredictionQuery query);

    List<PredictionFeatureMapping> features(PredictionQuery query);

    List<PredictionDisplay> latest(PredictionQuery query);

    PredictionBatchDetail batchDetail(Long batchId);

    List<PredictionRun> runs(Long batchId);

    PredictionCompleteness completeness(Long batchId);

    List<MetricSeriesPoint> series(PredictionQuery query);

    List<MetricSeriesPoint> predictionSeries(PredictionQuery query);

    PredictionBatch resolveBatch(PredictionQuery query);

    EventPredictionTrace eventTrace(Long eventId);
}
