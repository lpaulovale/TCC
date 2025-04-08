package com.auth.redis.repository.redis;

import java.util.Optional;

import org.springframework.data.repository.CrudRepository;
import org.springframework.stereotype.Repository;

import com.auth.redis.model.UserToken;

@Repository
public interface TokenRepository extends CrudRepository<UserToken, String> {
    Optional<UserToken> findByToken(String token);
    void deleteByUserId(String userId);
}