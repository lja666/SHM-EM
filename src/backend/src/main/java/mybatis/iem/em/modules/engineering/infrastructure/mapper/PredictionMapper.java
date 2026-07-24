package mybatis.iem.em.modules.engineering.infrastructure.mapper;

import mybatis.iem.em.modules.engineering.application.dto.PredictionQuery;
import mybatis.iem.em.modules.engineering.domain.model.PredictionBatch;
import mybatis.iem.em.modules.engineering.domain.model.PredictionDisplay;
import mybatis.iem.em.modules.engineering.domain.model.PredictionFeatureMapping;
import mybatis.iem.em.modules.engineering.domain.model.PredictionModel;
import mybatis.iem.em.modules.engineering.domain.model.PredictionRun;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface PredictionMapper {
    List<PredictionBatch> selectBatches(@Param("query") PredictionQuery query, @Param("limit") Integer limit);

    List<PredictionModel> selectModels(@Param("query") PredictionQuery query, @Param("limit") Integer limit);

    List<PredictionFeatureMapping> selectFeatures(@Param("query") PredictionQuery query, @Param("limit") Integer limit);

    List<PredictionDisplay> selectSeries(@Param("query") PredictionQuery query, @Param("limit") Integer limit);

    PredictionBatch selectBatchById(@Param("batchId") Long batchId);

    List<PredictionRun> selectRunsByBatch(@Param("batchId") Long batchId);
}
