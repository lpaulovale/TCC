package com.auth.redis.model;

public class ResponseType {
    private String message;
    private String version;
    
    // Default constructor required for Jackson
    public ResponseType() {}
    
    // Getters and setters
    public String getMessage() {
        return message;
    }
    
    public void setMessage(String message) {
        this.message = message;
    }
    
    public String getVersion() {
        return version;
    }
    
    public void setVersion(String version) {
        this.version = version;
    }
}