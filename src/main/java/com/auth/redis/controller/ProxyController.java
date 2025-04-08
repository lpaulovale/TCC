package com.auth.redis.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.auth.redis.model.ResponseType;
import com.auth.redis.service.ExternalApiService;
@RestController
@RequestMapping("/api")
public class ProxyController {
    
    private final ExternalApiService externalApiService;
    
    public ProxyController(ExternalApiService externalApiService) {
        this.externalApiService = externalApiService;
    }

    @GetMapping("/test")
public String testAuth() {
    return "You are authenticated!";
}

    @GetMapping("/external-data")
    public ResponseType getExternalData() {  // Changed from Mono<ResponseType>
        return externalApiService.getExternalData();
    }
}