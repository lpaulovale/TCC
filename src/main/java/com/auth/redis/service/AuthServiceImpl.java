package com.auth.redis.service;

import java.util.*;

import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import com.auth.redis.model.Role;
import com.auth.redis.model.User;
import com.auth.redis.model.UserToken;
import com.auth.redis.repository.jpa.RoleRepository;
import com.auth.redis.repository.jpa.UserRepository;
import com.auth.redis.repository.redis.TokenRepository;
import com.auth.redis.security.JwtTokenProvider;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class AuthServiceImpl implements AuthService {

    private final UserRepository userRepository;
    private final RoleRepository roleRepository;
    private final TokenRepository tokenRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;

    @Override
    public Map<String, Object> login(String username, String password) {
        Optional<User> userOpt = userRepository.findByUsername(username);

        if (userOpt.isEmpty() || !passwordEncoder.matches(password, userOpt.get().getPasswordHash())) {
            throw new RuntimeException("Invalid username or password");
        }

        User user = userOpt.get();
        String token = jwtTokenProvider.generateToken(user);

        UserToken userToken = UserToken.builder()
                .id(UUID.randomUUID().toString())
                .userId(String.valueOf(user.getId()))
                .token(token)
                .ttl(jwtTokenProvider.getExpirationInSeconds())
                .build();

        tokenRepository.save(userToken);

        Map<String, Object> response = new HashMap<>();
        response.put("token", token);
        response.put("userId", user.getId());
        response.put("username", user.getUsername());

        return response;
    }

    @Override
    public User register(String username, String email, String password) {
        User user = new User();
        user.setUsername(username);
        user.setEmail(email);
        user.setPassword(passwordEncoder.encode(password));
        user.setActive(true);

        Role userRole = roleRepository.findByName("ROLE_USER")
            .orElseThrow(() -> new RuntimeException("Default role not found"));

        user.setRoles(Set.of(userRole));

        return userRepository.save(user);
    }

    @Override
    public void logout(String userId) {
        tokenRepository.deleteByUserId(userId);
    }
}
