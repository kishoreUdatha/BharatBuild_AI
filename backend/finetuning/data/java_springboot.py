"""
Java + Spring Boot Training Data Generator
Generates training samples for Java backend development
"""
import json
from pathlib import Path


JAVA_SPRINGBOOT_SAMPLES = [
    {
        "messages": [
            {"role": "system", "content": "You are an expert Java Spring Boot developer."},
            {"role": "user", "content": "Create a Spring Boot User entity with JPA annotations and relationships"},
            {"role": "assistant", "content": """```java
package com.example.app.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

@Entity
@Table(name = "users")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, unique = true)
    private String email;

    @Column(nullable = false)
    private String name;

    @Column(nullable = false)
    private String password;

    @Column(name = "avatar_url")
    private String avatarUrl;

    @Column(name = "is_active")
    @Builder.Default
    private Boolean isActive = true;

    @Column(name = "is_verified")
    @Builder.Default
    private Boolean isVerified = false;

    @Enumerated(EnumType.STRING)
    @Builder.Default
    private Role role = Role.USER;

    @OneToMany(mappedBy = "user", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private Set<Project> projects = new HashSet<>();

    @OneToMany(mappedBy = "user", cascade = CascadeType.ALL)
    @Builder.Default
    private Set<Token> tokens = new HashSet<>();

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    public enum Role {
        USER, ADMIN, MODERATOR
    }

    // Helper methods
    public void addProject(Project project) {
        projects.add(project);
        project.setUser(this);
    }

    public void removeProject(Project project) {
        projects.remove(project);
        project.setUser(null);
    }
}
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Java Spring Boot developer."},
            {"role": "user", "content": "Create a Spring Boot REST controller for user CRUD operations"},
            {"role": "assistant", "content": """```java
package com.example.app.controller;

import com.example.app.dto.UserCreateRequest;
import com.example.app.dto.UserResponse;
import com.example.app.dto.UserUpdateRequest;
import com.example.app.service.UserService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    @GetMapping
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Page<UserResponse>> getAllUsers(
            @RequestParam(required = false) String search,
            Pageable pageable) {
        Page<UserResponse> users = userService.findAll(search, pageable);
        return ResponseEntity.ok(users);
    }

    @GetMapping("/{id}")
    public ResponseEntity<UserResponse> getUserById(@PathVariable UUID id) {
        UserResponse user = userService.findById(id);
        return ResponseEntity.ok(user);
    }

    @PostMapping
    public ResponseEntity<UserResponse> createUser(
            @Valid @RequestBody UserCreateRequest request) {
        UserResponse user = userService.create(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(user);
    }

    @PutMapping("/{id}")
    public ResponseEntity<UserResponse> updateUser(
            @PathVariable UUID id,
            @Valid @RequestBody UserUpdateRequest request) {
        UserResponse user = userService.update(id, request);
        return ResponseEntity.ok(user);
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Void> deleteUser(@PathVariable UUID id) {
        userService.delete(id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/me")
    public ResponseEntity<UserResponse> getCurrentUser() {
        UserResponse user = userService.getCurrentUser();
        return ResponseEntity.ok(user);
    }

    @PatchMapping("/me")
    public ResponseEntity<UserResponse> updateCurrentUser(
            @Valid @RequestBody UserUpdateRequest request) {
        UserResponse user = userService.updateCurrentUser(request);
        return ResponseEntity.ok(user);
    }
}
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Java Spring Boot developer."},
            {"role": "user", "content": "Create a Spring Boot service layer for user management with exception handling"},
            {"role": "assistant", "content": """```java
package com.example.app.service;

import com.example.app.dto.UserCreateRequest;
import com.example.app.dto.UserResponse;
import com.example.app.dto.UserUpdateRequest;
import com.example.app.entity.User;
import com.example.app.exception.ResourceNotFoundException;
import com.example.app.exception.DuplicateResourceException;
import com.example.app.mapper.UserMapper;
import com.example.app.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
@Transactional
public class UserService {

    private final UserRepository userRepository;
    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;

    @Transactional(readOnly = true)
    public Page<UserResponse> findAll(String search, Pageable pageable) {
        Page<User> users;
        if (search != null && !search.isBlank()) {
            users = userRepository.findByNameContainingIgnoreCaseOrEmailContainingIgnoreCase(
                    search, search, pageable);
        } else {
            users = userRepository.findAll(pageable);
        }
        return users.map(userMapper::toResponse);
    }

    @Transactional(readOnly = true)
    public UserResponse findById(UUID id) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("User", "id", id));
        return userMapper.toResponse(user);
    }

    public UserResponse create(UserCreateRequest request) {
        // Check for duplicate email
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new DuplicateResourceException("User", "email", request.getEmail());
        }

        User user = userMapper.toEntity(request);
        user.setPassword(passwordEncoder.encode(request.getPassword()));

        User savedUser = userRepository.save(user);
        log.info("Created user with id: {}", savedUser.getId());

        return userMapper.toResponse(savedUser);
    }

    public UserResponse update(UUID id, UserUpdateRequest request) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("User", "id", id));

        userMapper.updateEntity(user, request);
        User updatedUser = userRepository.save(user);

        log.info("Updated user with id: {}", id);
        return userMapper.toResponse(updatedUser);
    }

    public void delete(UUID id) {
        if (!userRepository.existsById(id)) {
            throw new ResourceNotFoundException("User", "id", id);
        }
        userRepository.deleteById(id);
        log.info("Deleted user with id: {}", id);
    }

    @Transactional(readOnly = true)
    public UserResponse getCurrentUser() {
        String email = SecurityContextHolder.getContext().getAuthentication().getName();
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new ResourceNotFoundException("User", "email", email));
        return userMapper.toResponse(user);
    }

    public UserResponse updateCurrentUser(UserUpdateRequest request) {
        String email = SecurityContextHolder.getContext().getAuthentication().getName();
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new ResourceNotFoundException("User", "email", email));

        userMapper.updateEntity(user, request);
        User updatedUser = userRepository.save(user);

        return userMapper.toResponse(updatedUser);
    }
}
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Java Spring Boot developer."},
            {"role": "user", "content": "Create Spring Boot DTOs with validation for user registration"},
            {"role": "assistant", "content": """```java
package com.example.app.dto;

import jakarta.validation.constraints.*;
import lombok.*;

import java.time.LocalDateTime;
import java.util.UUID;

// Request DTOs
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserCreateRequest {

    @NotBlank(message = "Name is required")
    @Size(min = 2, max = 100, message = "Name must be between 2 and 100 characters")
    private String name;

    @NotBlank(message = "Email is required")
    @Email(message = "Invalid email format")
    private String email;

    @NotBlank(message = "Password is required")
    @Size(min = 8, message = "Password must be at least 8 characters")
    @Pattern(
        regexp = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).*$",
        message = "Password must contain at least one uppercase, one lowercase, and one digit"
    )
    private String password;

    @NotBlank(message = "Password confirmation is required")
    private String passwordConfirm;

    @AssertTrue(message = "Passwords do not match")
    public boolean isPasswordMatching() {
        return password != null && password.equals(passwordConfirm);
    }
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserUpdateRequest {

    @Size(min = 2, max = 100, message = "Name must be between 2 and 100 characters")
    private String name;

    private String avatarUrl;

    @Size(max = 500, message = "Bio must not exceed 500 characters")
    private String bio;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChangePasswordRequest {

    @NotBlank(message = "Current password is required")
    private String currentPassword;

    @NotBlank(message = "New password is required")
    @Size(min = 8, message = "Password must be at least 8 characters")
    private String newPassword;

    @NotBlank(message = "Password confirmation is required")
    private String newPasswordConfirm;

    @AssertTrue(message = "Passwords do not match")
    public boolean isPasswordMatching() {
        return newPassword != null && newPassword.equals(newPasswordConfirm);
    }
}

// Response DTOs
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserResponse {
    private UUID id;
    private String name;
    private String email;
    private String avatarUrl;
    private Boolean isVerified;
    private String role;
    private LocalDateTime createdAt;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ApiResponse<T> {
    private boolean success;
    private String message;
    private T data;

    public static <T> ApiResponse<T> success(T data) {
        return ApiResponse.<T>builder()
                .success(true)
                .data(data)
                .build();
    }

    public static <T> ApiResponse<T> success(String message, T data) {
        return ApiResponse.<T>builder()
                .success(true)
                .message(message)
                .data(data)
                .build();
    }

    public static <T> ApiResponse<T> error(String message) {
        return ApiResponse.<T>builder()
                .success(false)
                .message(message)
                .build();
    }
}
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Java Spring Boot developer."},
            {"role": "user", "content": "Create Spring Boot JWT authentication configuration with Spring Security"},
            {"role": "assistant", "content": """```java
package com.example.app.config;

import com.example.app.security.JwtAuthenticationFilter;
import com.example.app.security.JwtAuthenticationEntryPoint;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.AuthenticationProvider;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.List;

@Configuration
@EnableWebSecurity
@EnableMethodSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtAuthenticationFilter jwtAuthFilter;
    private final JwtAuthenticationEntryPoint authEntryPoint;
    private final UserDetailsService userDetailsService;

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .cors(cors -> cors.configurationSource(corsConfigurationSource()))
            .csrf(AbstractHttpConfigurer::disable)
            .exceptionHandling(ex -> ex.authenticationEntryPoint(authEntryPoint))
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers(
                    "/api/v1/auth/**",
                    "/api/v1/public/**",
                    "/swagger-ui/**",
                    "/v3/api-docs/**",
                    "/actuator/health"
                ).permitAll()
                .requestMatchers("/api/v1/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .authenticationProvider(authenticationProvider())
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    @Bean
    public AuthenticationProvider authenticationProvider() {
        DaoAuthenticationProvider provider = new DaoAuthenticationProvider();
        provider.setUserDetailsService(userDetailsService);
        provider.setPasswordEncoder(passwordEncoder());
        return provider;
    }

    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration config) throws Exception {
        return config.getAuthenticationManager();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(List.of("http://localhost:3000", "https://yourdomain.com"));
        configuration.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(List.of("*"));
        configuration.setAllowCredentials(true);
        configuration.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }
}
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Java Spring Boot developer."},
            {"role": "user", "content": "Create a Spring Boot JWT utility class for token generation and validation"},
            {"role": "assistant", "content": """```java
package com.example.app.security;

import io.jsonwebtoken.*;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.stereotype.Component;

import java.security.Key;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.function.Function;

@Component
@Slf4j
public class JwtUtils {

    @Value("${jwt.secret}")
    private String secretKey;

    @Value("${jwt.access-token-expiration}")
    private long accessTokenExpiration;

    @Value("${jwt.refresh-token-expiration}")
    private long refreshTokenExpiration;

    public String generateAccessToken(UserDetails userDetails) {
        return generateToken(new HashMap<>(), userDetails, accessTokenExpiration);
    }

    public String generateAccessToken(Map<String, Object> extraClaims, UserDetails userDetails) {
        return generateToken(extraClaims, userDetails, accessTokenExpiration);
    }

    public String generateRefreshToken(UserDetails userDetails) {
        return generateToken(new HashMap<>(), userDetails, refreshTokenExpiration);
    }

    private String generateToken(Map<String, Object> extraClaims, UserDetails userDetails, long expiration) {
        return Jwts.builder()
                .setClaims(extraClaims)
                .setSubject(userDetails.getUsername())
                .setIssuedAt(new Date(System.currentTimeMillis()))
                .setExpiration(new Date(System.currentTimeMillis() + expiration))
                .signWith(getSigningKey(), SignatureAlgorithm.HS256)
                .compact();
    }

    public String extractUsername(String token) {
        return extractClaim(token, Claims::getSubject);
    }

    public Date extractExpiration(String token) {
        return extractClaim(token, Claims::getExpiration);
    }

    public <T> T extractClaim(String token, Function<Claims, T> claimsResolver) {
        final Claims claims = extractAllClaims(token);
        return claimsResolver.apply(claims);
    }

    private Claims extractAllClaims(String token) {
        return Jwts.parserBuilder()
                .setSigningKey(getSigningKey())
                .build()
                .parseClaimsJws(token)
                .getBody();
    }

    public boolean isTokenValid(String token, UserDetails userDetails) {
        try {
            final String username = extractUsername(token);
            return username.equals(userDetails.getUsername()) && !isTokenExpired(token);
        } catch (JwtException | IllegalArgumentException e) {
            log.error("Invalid JWT token: {}", e.getMessage());
            return false;
        }
    }

    public boolean isTokenExpired(String token) {
        return extractExpiration(token).before(new Date());
    }

    public boolean validateToken(String token) {
        try {
            Jwts.parserBuilder()
                    .setSigningKey(getSigningKey())
                    .build()
                    .parseClaimsJws(token);
            return true;
        } catch (MalformedJwtException e) {
            log.error("Invalid JWT token: {}", e.getMessage());
        } catch (ExpiredJwtException e) {
            log.error("JWT token is expired: {}", e.getMessage());
        } catch (UnsupportedJwtException e) {
            log.error("JWT token is unsupported: {}", e.getMessage());
        } catch (IllegalArgumentException e) {
            log.error("JWT claims string is empty: {}", e.getMessage());
        }
        return false;
    }

    private Key getSigningKey() {
        byte[] keyBytes = Decoders.BASE64.decode(secretKey);
        return Keys.hmacShaKeyFor(keyBytes);
    }
}
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Java Spring Boot developer."},
            {"role": "user", "content": "Create a Spring Boot authentication controller with login, register, and refresh token endpoints"},
            {"role": "assistant", "content": """```java
package com.example.app.controller;

import com.example.app.dto.*;
import com.example.app.service.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/register")
    public ResponseEntity<AuthResponse> register(@Valid @RequestBody RegisterRequest request) {
        AuthResponse response = authService.register(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @PostMapping("/login")
    public ResponseEntity<AuthResponse> login(@Valid @RequestBody LoginRequest request) {
        AuthResponse response = authService.login(request);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/refresh")
    public ResponseEntity<AuthResponse> refreshToken(@Valid @RequestBody RefreshTokenRequest request) {
        AuthResponse response = authService.refreshToken(request);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/logout")
    public ResponseEntity<Void> logout(@RequestHeader("Authorization") String token) {
        authService.logout(token.substring(7));
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/forgot-password")
    public ResponseEntity<ApiResponse<Void>> forgotPassword(
            @Valid @RequestBody ForgotPasswordRequest request) {
        authService.forgotPassword(request);
        return ResponseEntity.ok(ApiResponse.success("Password reset email sent", null));
    }

    @PostMapping("/reset-password")
    public ResponseEntity<ApiResponse<Void>> resetPassword(
            @Valid @RequestBody ResetPasswordRequest request) {
        authService.resetPassword(request);
        return ResponseEntity.ok(ApiResponse.success("Password reset successful", null));
    }

    @PostMapping("/verify-email")
    public ResponseEntity<ApiResponse<Void>> verifyEmail(@RequestParam String token) {
        authService.verifyEmail(token);
        return ResponseEntity.ok(ApiResponse.success("Email verified successfully", null));
    }
}

// Auth DTOs
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
class RegisterRequest {
    @NotBlank
    private String name;

    @NotBlank
    @Email
    private String email;

    @NotBlank
    @Size(min = 8)
    private String password;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
class LoginRequest {
    @NotBlank
    @Email
    private String email;

    @NotBlank
    private String password;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
class AuthResponse {
    private String accessToken;
    private String refreshToken;
    private String tokenType;
    private Long expiresIn;
    private UserResponse user;
}

@Data
@NoArgsConstructor
@AllArgsConstructor
class RefreshTokenRequest {
    @NotBlank
    private String refreshToken;
}
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Java Spring Boot developer."},
            {"role": "user", "content": "Create a Spring Boot repository with custom queries using Spring Data JPA"},
            {"role": "assistant", "content": """```java
package com.example.app.repository;

import com.example.app.entity.Product;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface ProductRepository extends JpaRepository<Product, UUID>, JpaSpecificationExecutor<Product> {

    // Find by field
    Optional<Product> findBySlug(String slug);

    List<Product> findByIsActiveTrue();

    // Search with pagination
    Page<Product> findByNameContainingIgnoreCase(String name, Pageable pageable);

    // Custom JPQL query
    @Query("SELECT p FROM Product p WHERE p.category.id = :categoryId AND p.isActive = true")
    Page<Product> findByCategoryId(@Param("categoryId") UUID categoryId, Pageable pageable);

    // Price range query
    @Query("SELECT p FROM Product p WHERE p.price BETWEEN :minPrice AND :maxPrice AND p.isActive = true")
    List<Product> findByPriceRange(
            @Param("minPrice") BigDecimal minPrice,
            @Param("maxPrice") BigDecimal maxPrice);

    // Complex search query
    @Query("SELECT p FROM Product p " +
           "WHERE (:search IS NULL OR LOWER(p.name) LIKE LOWER(CONCAT('%', :search, '%'))) " +
           "AND (:categoryId IS NULL OR p.category.id = :categoryId) " +
           "AND (:minPrice IS NULL OR p.price >= :minPrice) " +
           "AND (:maxPrice IS NULL OR p.price <= :maxPrice) " +
           "AND p.isActive = true")
    Page<Product> searchProducts(
            @Param("search") String search,
            @Param("categoryId") UUID categoryId,
            @Param("minPrice") BigDecimal minPrice,
            @Param("maxPrice") BigDecimal maxPrice,
            Pageable pageable);

    // Native query
    @Query(value = "SELECT p.* FROM products p " +
           "LEFT JOIN order_items oi ON p.id = oi.product_id " +
           "WHERE p.is_active = true " +
           "GROUP BY p.id " +
           "ORDER BY COUNT(oi.id) DESC " +
           "LIMIT :limit", nativeQuery = true)
    List<Product> findBestSellers(@Param("limit") int limit);

    // Aggregate query
    @Query("SELECT AVG(p.price) FROM Product p WHERE p.category.id = :categoryId")
    BigDecimal findAveragePriceByCategory(@Param("categoryId") UUID categoryId);

    // Count query
    @Query("SELECT COUNT(p) FROM Product p WHERE p.category.id = :categoryId AND p.isActive = true")
    long countByCategoryId(@Param("categoryId") UUID categoryId);

    // Update query
    @Modifying
    @Query("UPDATE Product p SET p.isActive = false WHERE p.id IN :ids")
    int deactivateProducts(@Param("ids") List<UUID> ids);

    // Exists query
    boolean existsBySlug(String slug);

    // Delete query
    @Modifying
    @Query("DELETE FROM Product p WHERE p.isActive = false AND p.updatedAt < :date")
    int deleteInactiveOlderThan(@Param("date") java.time.LocalDateTime date);
}
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Java Spring Boot developer."},
            {"role": "user", "content": "Create Spring Boot global exception handler with custom exceptions"},
            {"role": "assistant", "content": """```java
package com.example.app.exception;

import lombok.Getter;
import org.springframework.http.HttpStatus;

// Custom Exceptions
@Getter
public class ResourceNotFoundException extends RuntimeException {
    private final String resourceName;
    private final String fieldName;
    private final Object fieldValue;

    public ResourceNotFoundException(String resourceName, String fieldName, Object fieldValue) {
        super(String.format("%s not found with %s: '%s'", resourceName, fieldName, fieldValue));
        this.resourceName = resourceName;
        this.fieldName = fieldName;
        this.fieldValue = fieldValue;
    }
}

@Getter
public class DuplicateResourceException extends RuntimeException {
    private final String resourceName;
    private final String fieldName;
    private final Object fieldValue;

    public DuplicateResourceException(String resourceName, String fieldName, Object fieldValue) {
        super(String.format("%s already exists with %s: '%s'", resourceName, fieldName, fieldValue));
        this.resourceName = resourceName;
        this.fieldName = fieldName;
        this.fieldValue = fieldValue;
    }
}

public class UnauthorizedException extends RuntimeException {
    public UnauthorizedException(String message) {
        super(message);
    }
}

// Global Exception Handler
package com.example.app.exception;

import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleResourceNotFound(ResourceNotFoundException ex) {
        log.error("Resource not found: {}", ex.getMessage());
        return ResponseEntity
                .status(HttpStatus.NOT_FOUND)
                .body(ErrorResponse.of(HttpStatus.NOT_FOUND, ex.getMessage()));
    }

    @ExceptionHandler(DuplicateResourceException.class)
    public ResponseEntity<ErrorResponse> handleDuplicateResource(DuplicateResourceException ex) {
        log.error("Duplicate resource: {}", ex.getMessage());
        return ResponseEntity
                .status(HttpStatus.CONFLICT)
                .body(ErrorResponse.of(HttpStatus.CONFLICT, ex.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidationErrors(MethodArgumentNotValidException ex) {
        Map<String, String> errors = new HashMap<>();
        ex.getBindingResult().getAllErrors().forEach(error -> {
            String fieldName = ((FieldError) error).getField();
            String message = error.getDefaultMessage();
            errors.put(fieldName, message);
        });

        ErrorResponse response = ErrorResponse.builder()
                .status(HttpStatus.BAD_REQUEST.value())
                .error("Validation Failed")
                .message("Invalid input data")
                .timestamp(LocalDateTime.now())
                .validationErrors(errors)
                .build();

        return ResponseEntity.badRequest().body(response);
    }

    @ExceptionHandler(BadCredentialsException.class)
    public ResponseEntity<ErrorResponse> handleBadCredentials(BadCredentialsException ex) {
        return ResponseEntity
                .status(HttpStatus.UNAUTHORIZED)
                .body(ErrorResponse.of(HttpStatus.UNAUTHORIZED, "Invalid email or password"));
    }

    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<ErrorResponse> handleAccessDenied(AccessDeniedException ex) {
        return ResponseEntity
                .status(HttpStatus.FORBIDDEN)
                .body(ErrorResponse.of(HttpStatus.FORBIDDEN, "Access denied"));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGenericException(Exception ex) {
        log.error("Unexpected error", ex);
        return ResponseEntity
                .status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ErrorResponse.of(HttpStatus.INTERNAL_SERVER_ERROR, "An unexpected error occurred"));
    }
}

// Error Response DTO
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
class ErrorResponse {
    private int status;
    private String error;
    private String message;
    private LocalDateTime timestamp;
    private Map<String, String> validationErrors;

    public static ErrorResponse of(HttpStatus status, String message) {
        return ErrorResponse.builder()
                .status(status.value())
                .error(status.getReasonPhrase())
                .message(message)
                .timestamp(LocalDateTime.now())
                .build();
    }
}
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Java Spring Boot developer."},
            {"role": "user", "content": "Create a Spring Boot Product entity with category relationship and inventory tracking"},
            {"role": "assistant", "content": """```java
package com.example.app.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "products")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Product {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false)
    private String name;

    @Column(unique = true, nullable = false)
    private String slug;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "short_description", length = 500)
    private String shortDescription;

    // Pricing
    @Column(nullable = false, precision = 10, scale = 2)
    private BigDecimal price;

    @Column(name = "compare_at_price", precision = 10, scale = 2)
    private BigDecimal compareAtPrice;

    @Column(name = "cost_price", precision = 10, scale = 2)
    private BigDecimal costPrice;

    // Inventory
    @Column(unique = true)
    private String sku;

    private String barcode;

    @Column(nullable = false)
    @Builder.Default
    private Integer quantity = 0;

    @Column(name = "low_stock_threshold")
    @Builder.Default
    private Integer lowStockThreshold = 10;

    @Column(name = "track_inventory")
    @Builder.Default
    private Boolean trackInventory = true;

    // Status
    @Enumerated(EnumType.STRING)
    @Builder.Default
    private ProductStatus status = ProductStatus.DRAFT;

    @Column(name = "is_active")
    @Builder.Default
    private Boolean isActive = true;

    @Column(name = "is_featured")
    @Builder.Default
    private Boolean isFeatured = false;

    // SEO
    @Column(name = "meta_title")
    private String metaTitle;

    @Column(name = "meta_description", length = 500)
    private String metaDescription;

    // Media
    @ElementCollection
    @CollectionTable(name = "product_images", joinColumns = @JoinColumn(name = "product_id"))
    @Builder.Default
    private List<ProductImage> images = new ArrayList<>();

    @Column(name = "thumbnail_url")
    private String thumbnailUrl;

    // Relationships
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "category_id")
    private Category category;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "brand_id")
    private Brand brand;

    @OneToMany(mappedBy = "product", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<ProductVariant> variants = new ArrayList<>();

    @OneToMany(mappedBy = "product", cascade = CascadeType.ALL)
    @Builder.Default
    private List<Review> reviews = new ArrayList<>();

    // Audit
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "created_by")
    private User createdBy;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    // Computed properties
    @Transient
    public boolean isOnSale() {
        return compareAtPrice != null && compareAtPrice.compareTo(price) > 0;
    }

    @Transient
    public BigDecimal getDiscountPercentage() {
        if (!isOnSale()) return BigDecimal.ZERO;
        return BigDecimal.ONE
                .subtract(price.divide(compareAtPrice, 2, java.math.RoundingMode.HALF_UP))
                .multiply(BigDecimal.valueOf(100));
    }

    @Transient
    public boolean isInStock() {
        if (!trackInventory) return true;
        return quantity > 0;
    }

    @Transient
    public boolean isLowStock() {
        if (!trackInventory) return false;
        return quantity <= lowStockThreshold;
    }

    @Transient
    public Double getAverageRating() {
        if (reviews.isEmpty()) return 0.0;
        return reviews.stream()
                .mapToInt(Review::getRating)
                .average()
                .orElse(0.0);
    }

    public enum ProductStatus {
        DRAFT, ACTIVE, OUT_OF_STOCK, DISCONTINUED
    }
}

@Embeddable
@Data
@NoArgsConstructor
@AllArgsConstructor
class ProductImage {
    private String url;
    private String alt;
    private Integer position;
}
```"""}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert Java Spring Boot developer."},
            {"role": "user", "content": "Create a Spring Boot MapStruct mapper for entity to DTO conversion"},
            {"role": "assistant", "content": """```java
package com.example.app.mapper;

import com.example.app.dto.*;
import com.example.app.entity.User;
import com.example.app.entity.Product;
import org.mapstruct.*;

import java.util.List;

@Mapper(componentModel = "spring", unmappedTargetPolicy = ReportingPolicy.IGNORE)
public interface UserMapper {

    @Mapping(target = "role", expression = "java(user.getRole().name())")
    UserResponse toResponse(User user);

    List<UserResponse> toResponseList(List<User> users);

    @Mapping(target = "id", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    @Mapping(target = "updatedAt", ignore = true)
    @Mapping(target = "password", ignore = true)
    @Mapping(target = "isVerified", constant = "false")
    @Mapping(target = "isActive", constant = "true")
    User toEntity(UserCreateRequest request);

    @BeanMapping(nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    void updateEntity(@MappingTarget User user, UserUpdateRequest request);
}

@Mapper(componentModel = "spring", unmappedTargetPolicy = ReportingPolicy.IGNORE)
public interface ProductMapper {

    @Mapping(target = "categoryId", source = "category.id")
    @Mapping(target = "categoryName", source = "category.name")
    @Mapping(target = "brandId", source = "brand.id")
    @Mapping(target = "brandName", source = "brand.name")
    @Mapping(target = "isOnSale", expression = "java(product.isOnSale())")
    @Mapping(target = "discountPercentage", expression = "java(product.getDiscountPercentage())")
    @Mapping(target = "isInStock", expression = "java(product.isInStock())")
    @Mapping(target = "averageRating", expression = "java(product.getAverageRating())")
    @Mapping(target = "reviewCount", expression = "java(product.getReviews().size())")
    ProductResponse toResponse(Product product);

    List<ProductResponse> toResponseList(List<Product> products);

    @Mapping(target = "id", ignore = true)
    @Mapping(target = "slug", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    @Mapping(target = "updatedAt", ignore = true)
    @Mapping(target = "category", ignore = true)
    @Mapping(target = "brand", ignore = true)
    @Mapping(target = "createdBy", ignore = true)
    Product toEntity(ProductCreateRequest request);

    @BeanMapping(nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    @Mapping(target = "category", ignore = true)
    @Mapping(target = "brand", ignore = true)
    void updateEntity(@MappingTarget Product product, ProductUpdateRequest request);

    // Custom mapping method
    default String mapCategoryToName(Category category) {
        return category != null ? category.getName() : null;
    }
}

// Product DTOs
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
class ProductResponse {
    private UUID id;
    private String name;
    private String slug;
    private String description;
    private BigDecimal price;
    private BigDecimal compareAtPrice;
    private String sku;
    private Integer quantity;
    private String status;
    private Boolean isActive;
    private Boolean isFeatured;
    private UUID categoryId;
    private String categoryName;
    private UUID brandId;
    private String brandName;
    private List<ProductImage> images;
    private String thumbnailUrl;
    private Boolean isOnSale;
    private BigDecimal discountPercentage;
    private Boolean isInStock;
    private Double averageRating;
    private Integer reviewCount;
    private LocalDateTime createdAt;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
class ProductCreateRequest {
    @NotBlank
    private String name;
    private String description;
    @NotNull
    @Positive
    private BigDecimal price;
    private BigDecimal compareAtPrice;
    private String sku;
    private Integer quantity;
    private UUID categoryId;
    private UUID brandId;
}
```"""}
        ]
    },
]


def generate_java_samples():
    """Generate all Java/Spring Boot samples"""
    all_samples = []

    # Add base samples
    all_samples.extend(JAVA_SPRINGBOOT_SAMPLES)

    # Augment with variations
    augmented = []
    for sample in all_samples:
        augmented.append(sample)
        # Add "Please" variation
        var = {"messages": sample["messages"].copy()}
        user_content = sample["messages"][1]["content"]
        var["messages"] = [
            sample["messages"][0],
            {"role": "user", "content": "Please " + user_content[0].lower() + user_content[1:]},
            sample["messages"][2]
        ]
        augmented.append(var)

    return augmented


def save_java_samples(output_dir: str = "./data/additional"):
    """Save Java/Spring Boot samples to file"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    samples = generate_java_samples()

    output_file = Path(output_dir) / "java_springboot.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    print(f"Generated {len(samples)} Java/Spring Boot samples")
    print(f"Saved to: {output_file}")

    return samples


if __name__ == "__main__":
    save_java_samples()
