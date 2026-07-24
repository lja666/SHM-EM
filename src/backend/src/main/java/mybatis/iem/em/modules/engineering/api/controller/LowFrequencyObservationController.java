package mybatis.iem.em.modules.engineering.api.controller;

import mybatis.iem.em.common.ApiResponse;
import mybatis.iem.em.modules.engineering.domain.model.LowFrequencyObservation;
import mybatis.iem.em.modules.engineering.application.dto.ObservationQuery;
import mybatis.iem.em.modules.engineering.application.service.LowFrequencyObservationService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/em/observations/low-frequency")
public class LowFrequencyObservationController {
    private final LowFrequencyObservationService service;

    public LowFrequencyObservationController(LowFrequencyObservationService service) {
        this.service = service;
    }

    @GetMapping
    public ApiResponse<List<LowFrequencyObservation>> list(@ModelAttribute ObservationQuery query) {
        return ApiResponse.ok(service.list(query));
    }

    @PostMapping("/query")
    public ApiResponse<List<LowFrequencyObservation>> query(@RequestBody ObservationQuery query) {
        return ApiResponse.ok(service.list(query));
    }

    @PostMapping("/timeseries")
    public ApiResponse<List<LowFrequencyObservation>> timeseries(@RequestBody ObservationQuery query) {
        return ApiResponse.ok(service.list(query));
    }
}





