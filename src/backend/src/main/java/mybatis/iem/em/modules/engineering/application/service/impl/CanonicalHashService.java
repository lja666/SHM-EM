package mybatis.iem.em.modules.engineering.application.service.impl;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
public class CanonicalHashService {
    private final ObjectMapper objectMapper;

    public CanonicalHashService(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public String canonicalJson(Object value) {
        return canonical(objectMapper.valueToTree(value), Collections.<String>emptySet());
    }

    public String canonicalJson(Object value, Set<String> excludedFields) {
        return canonical(objectMapper.valueToTree(value), excludedFields == null ? Collections.<String>emptySet() : excludedFields);
    }

    public String sha256Canonical(Object value) {
        return sha256(canonicalJson(value));
    }

    public String sha256Canonical(Object value, Set<String> excludedFields) {
        return sha256(canonicalJson(value, excludedFields));
    }

    private String canonical(JsonNode node, Set<String> excludedFields) {
        if (node == null || node.isNull()) {
            return "null";
        }
        if (node.isTextual()) {
            return quote(node.asText());
        }
        if (node.isNumber() || node.isBoolean()) {
            return node.toString();
        }
        if (node.isArray()) {
            List<String> values = new ArrayList<String>();
            for (JsonNode item : node) {
                values.add(canonical(item, excludedFields));
            }
            return "[" + String.join(",", values) + "]";
        }
        if (node.isObject()) {
            List<String> names = new ArrayList<String>();
            Iterator<String> iterator = node.fieldNames();
            while (iterator.hasNext()) {
                String name = iterator.next();
                if (!excludedFields.contains(name)) {
                    names.add(name);
                }
            }
            Collections.sort(names);
            List<String> entries = new ArrayList<String>();
            for (String name : names) {
                entries.add(quote(name) + ":" + canonical(node.get(name), excludedFields));
            }
            return "{" + String.join(",", entries) + "}";
        }
        return node.toString();
    }

    private String quote(String value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception ex) {
            throw new IllegalStateException("Failed to render canonical JSON string", ex);
        }
    }

    private String sha256(String material) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest(material.getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder();
            for (byte b : bytes) {
                builder.append(String.format("%02x", b));
            }
            return builder.toString();
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is not available", ex);
        }
    }
}
