package mybatis.iem.em.common;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {
    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(BusinessException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ApiResponse<Void> handleBusiness(BusinessException ex) {
        return ApiResponse.fail(ex.getCode(), ex.getMessage());
    }

    @ExceptionHandler(Exception.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public ApiResponse<Void> handleException(Exception ex) {
        log.error("Unhandled request exception", ex);
        if (isConnectionFailure(ex)) {
            return ApiResponse.fail(500, "Database connection failed. Check MySQL service and DB_URL/DB_USERNAME/DB_PASSWORD settings.");
        }
        return ApiResponse.fail(500, "Internal server error");
    }

    private boolean isConnectionFailure(Throwable ex) {
        Throwable current = ex;
        while (current != null) {
            String name = current.getClass().getName();
            String message = current.getMessage() == null ? "" : current.getMessage().toLowerCase();
            if (name.contains("CannotGetJdbcConnection")
                    || name.contains("GetConnectionTimeout")
                    || name.contains("CommunicationsException")
                    || message.contains("could not get jdbc connection")
                    || message.contains("failed to obtain jdbc connection")
                    || message.contains("connection refused")
                    || message.contains("access denied")) {
                return true;
            }
            current = current.getCause();
        }
        return false;
    }
}





