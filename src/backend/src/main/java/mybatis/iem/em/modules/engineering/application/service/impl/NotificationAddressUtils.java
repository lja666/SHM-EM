package mybatis.iem.em.modules.engineering.application.service.impl;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;

public final class NotificationAddressUtils {
    private static final Pattern EMAIL_PATTERN = Pattern.compile("^[A-Za-z0-9._%+\\-]+@[A-Za-z0-9.\\-]+\\.[A-Za-z]{2,}$");

    private NotificationAddressUtils() {
    }

    public static String normalizeToCommaText(String raw) {
        String[] values = parseValidArray(raw);
        if (values.length == 0) return null;
        StringBuilder builder = new StringBuilder();
        for (String value : values) {
            if (builder.length() > 0) builder.append(',');
            builder.append(value);
        }
        return builder.toString();
    }

    public static String[] parseValidArray(String raw) {
        if (!hasText(raw)) return new String[0];
        String normalized = raw.replace('；', ';')
                .replace('，', ',')
                .replace(';', ',')
                .replace('\n', ',')
                .replace('\r', ',')
                .replace('\t', ',');
        String[] parts = normalized.split(",");
        Set<String> values = new LinkedHashSet<String>();
        for (String part : parts) {
            if (!hasText(part)) continue;
            String email = part.trim();
            if (EMAIL_PATTERN.matcher(email).matches()) values.add(email);
        }
        List<String> list = new ArrayList<String>(values);
        return list.toArray(new String[list.size()]);
    }

    public static boolean hasText(String value) {
        return value != null && !value.trim().isEmpty();
    }
}
