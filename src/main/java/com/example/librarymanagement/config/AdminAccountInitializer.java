package com.example.librarymanagement.config;

import com.example.librarymanagement.entity.User;
import com.example.librarymanagement.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class AdminAccountInitializer implements ApplicationRunner {

    private static final Logger logger = LoggerFactory.getLogger(AdminAccountInitializer.class);

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final String username;
    private final String password;

    public AdminAccountInitializer(
            UserRepository userRepository,
            PasswordEncoder passwordEncoder,
            @Value("${library.admin.username:admin}") String username,
            @Value("${library.admin.password:}") String password) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.username = username.trim();
        this.password = password;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        if (password.isBlank()) {
            logger.warn("Admin account was not seeded. Set ADMIN_PASSWORD to initialize the first admin account.");
            return;
        }
        if (username.isBlank() || username.length() > 60) {
            throw new IllegalStateException("ADMIN_USERNAME must contain between 1 and 60 characters.");
        }
        if (password.length() < 12 || password.getBytes(java.nio.charset.StandardCharsets.UTF_8).length > 72) {
            throw new IllegalStateException("ADMIN_PASSWORD must be at least 12 characters and no more than 72 UTF-8 bytes.");
        }
        if (userRepository.existsByUsernameIgnoreCase(username)) {
            logger.info("Admin account '{}' already exists; its password was not changed.", username);
            return;
        }
        // Keep startup idempotent and store only the password encoder's BCrypt hash.
        userRepository.save(new User(username, passwordEncoder.encode(password), "ADMIN"));
        logger.info("Initial admin account '{}' was created with a BCrypt-hashed password.", username);
    }
}
