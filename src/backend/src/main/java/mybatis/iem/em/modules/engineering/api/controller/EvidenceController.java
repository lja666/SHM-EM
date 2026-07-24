package mybatis.iem.em.modules.engineering.api.controller;

import mybatis.iem.em.common.ApiResponse;
import mybatis.iem.em.modules.engineering.application.service.EvidenceService;
import mybatis.iem.em.modules.engineering.domain.model.Evidence;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/em/evidence")
public class EvidenceController {
    private final EvidenceService service;

    public EvidenceController(EvidenceService service) {
        this.service = service;
    }

    @GetMapping
    public ApiResponse<List<Evidence>> list(@RequestParam(required = false) Long projectId,
                                             @RequestParam(required = false) Integer limit) {
        return ApiResponse.ok(service.list(projectId, limit));
    }
}
