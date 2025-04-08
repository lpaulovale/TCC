package com.auth.redis.service;

import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import com.auth.redis.model.ResponseType;

@Service
public class ExternalApiService {
    
    private final RestTemplate restTemplate;
    private final String baseUrl = "http://python-server:5000";
    
    public ExternalApiService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    public ResponseType getExternalData() {
        return restTemplate.getForObject(baseUrl + "/", ResponseType.class);
    }
}