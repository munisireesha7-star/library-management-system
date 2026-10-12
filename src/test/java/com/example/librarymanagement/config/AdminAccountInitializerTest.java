package com.example.librarymanagement.config;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.example.librarymanagement.entity.User;
import com.example.librarymanagement.repository.UserRepository;
import org.junit.jupiter.api.Test;
import org.springframework.boot.DefaultApplicationArguments;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

class AdminAccountInitializerTest {

    @Test
    void seedsAdminWithHashedPassword() throws Exception {
        UserRepository userRepository = mock(UserRepository.class);
        PasswordEncoder passwordEncoder = new BCryptPasswordEncoder(4);
        String rawPassword = "a-unique-admin-password";
        AdminAccountInitializer initializer = new AdminAccountInitializer(
                userRepository, passwordEncoder, "admin", rawPassword);
        when(userRepository.existsByUsernameIgnoreCase("admin")).thenReturn(false);

        initializer.run(new DefaultApplicationArguments(new String[0]));

        var userCaptor = org.mockito.ArgumentCaptor.forClass(User.class);
        verify(userRepository).save(userCaptor.capture());
        User savedUser = userCaptor.getValue();
        assertTrue(passwordEncoder.matches(rawPassword, savedUser.getPassword()));
        assertNotEquals(rawPassword, savedUser.getPassword());
    }

    @Test
    void doesNotReplaceAnExistingAdmin() throws Exception {
        UserRepository userRepository = mock(UserRepository.class);
        AdminAccountInitializer initializer = new AdminAccountInitializer(
                userRepository, new BCryptPasswordEncoder(4), "admin", "a-unique-admin-password");
        when(userRepository.existsByUsernameIgnoreCase("admin")).thenReturn(true);

        initializer.run(new DefaultApplicationArguments(new String[0]));

        verify(userRepository, never()).save(any(User.class));
    }

    @Test
    void doesNotSeedWhenPasswordIsNotConfigured() throws Exception {
        UserRepository userRepository = mock(UserRepository.class);
        AdminAccountInitializer initializer = new AdminAccountInitializer(
                userRepository, new BCryptPasswordEncoder(4), "admin", "");

        initializer.run(new DefaultApplicationArguments(new String[0]));

        verify(userRepository, never()).save(any(User.class));
    }

    @Test
    void userEntityRejectsUnhashedPasswords() {
        org.junit.jupiter.api.Assertions.assertThrows(IllegalArgumentException.class,
                () -> new User("admin", "plain-text-password", "ADMIN"));
    }
}
