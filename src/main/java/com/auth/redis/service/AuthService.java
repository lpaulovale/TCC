package com.auth.redis.service;

import java.util.Map;

import com.auth.redis.model.User;

public interface AuthService {
    Map<String, Object> login(String username, String password);
    User register(String username, String email, String password);
    void logout(String userId);
}