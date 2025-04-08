package com.auth.redis.service;

import java.util.Optional;
import java.util.UUID;

import org.springframework.stereotype.Service;

import com.auth.redis.model.UserToken;
import com.auth.redis.repository.redis.TokenRepository;
import com.auth.redis.security.JwtTokenProvider;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class TokenService {

    private final TokenRepository tokenRepository;
    private final JwtTokenProvider tokenProvider;

    public UserToken saveToken(String userId, String tokenValue) {
        UserToken userToken = new UserToken();
        userToken.setId(UUID.randomUUID().toString());
        userToken.setUserId(userId);
        userToken.setToken(tokenValue);
        userToken.setTtl(tokenProvider.getExpirationInSeconds());
        
        return tokenRepository.save(userToken);
    }    

    public Optional<UserToken> findByToken(String token) {
        return tokenRepository.findByToken(token);
    }

    public void revokeToken(String token) {
        Optional<UserToken> tokenOpt = tokenRepository.findByToken(token);
        tokenOpt.ifPresent(userToken -> {
            userToken.setRevoked(true);
            tokenRepository.save(userToken);
        });
    }
    
    public boolean isTokenValid(String token) {
        Optional<UserToken> tokenOpt = tokenRepository.findByToken(token);
        return tokenOpt.isPresent() && !tokenOpt.get().isRevoked();
    }
}
