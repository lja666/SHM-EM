package mybatis.iem.em.modules.engineering.api.controller;

import mybatis.iem.em.common.ApiResponse;
import mybatis.iem.em.modules.engineering.domain.model.AccelerationWaveform;
import mybatis.iem.em.modules.engineering.application.dto.ObservationQuery;
import mybatis.iem.em.modules.engineering.application.service.AccelerationWaveformService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/em/acceleration")
public class AccelerationWaveformController {
    private final AccelerationWaveformService service;

    public AccelerationWaveformController(AccelerationWaveformService service) {
        this.service = service;
    }

    @GetMapping
    public ApiResponse<List<AccelerationWaveform>> list(@ModelAttribute ObservationQuery query) {
        return ApiResponse.ok(service.list(query));
    }

    @PostMapping("/waveform")
    public ApiResponse<List<AccelerationWaveform>> waveform(@RequestBody ObservationQuery query) {
        return ApiResponse.ok(service.list(query));
    }
}





