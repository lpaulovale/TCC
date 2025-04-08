package com.auth.redis.model;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.redis.core.RedisHash;
import org.springframework.data.redis.core.TimeToLive;
import org.springframework.data.redis.core.index.Indexed;

import java.util.concurrent.TimeUnit;

@Data
@NoArgsConstructor
@AllArgsConstructor
@RedisHash("token")
public class Token {

    @Id
    private String id;
    
    @Indexed
    private String userId;
    
    private String tokenValue;
    
    private boolean revoked = false;
    
    @TimeToLive(unit = TimeUnit.SECONDS)
    private Long expiration;
}