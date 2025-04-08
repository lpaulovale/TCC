package com.auth.redis.model;

import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.redis.core.RedisHash;

import java.io.Serializable;

@Data
@Builder  // Enables builder pattern
@NoArgsConstructor  // Required for Redis and Spring Data
@AllArgsConstructor // Ensures all fields have a constructor
@RedisHash("UserToken")
public class UserToken implements Serializable {
    
    @Id
    private String id;
    private String userId;
    private String token;
    private long ttl;
    private boolean revoked;  // Ensure all fields are included in the constructor

    public void setToken(String token) {
        this.token = token;
    }

    public void setTtl(long ttl) {  // ✅ Corrected setter
        this.ttl = ttl;
    }

    public boolean isRevoked() {
        return revoked;
    }

    public void setRevoked(boolean revoked) {
        this.revoked = revoked;
    }
}
