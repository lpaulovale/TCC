package com.auth.redis;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.domain.EntityScan;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.data.redis.repository.configuration.EnableRedisRepositories;

@SpringBootApplication
@EnableJpaRepositories(
    basePackages = "com.auth.redis.repository.jpa" // your JPA repositories
)
@EnableRedisRepositories(
    basePackages = "com.auth.redis.repository.redis" // your Redis repositories
)
@EntityScan("com.auth.redis.model")
public class RedisAuthApplication {
    public static void main(String[] args) {
        SpringApplication.run(RedisAuthApplication.class, args);
    }
}