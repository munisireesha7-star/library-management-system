package com.example.librarymanagement.exception;

import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.ui.Model;

@ControllerAdvice
public class GlobalExceptionHandler {

    @ModelAttribute("activeNav")
    public String activeNavigation(HttpServletRequest request) {
        String path = request.getRequestURI();
        if (path == null || path.equals("/") || path.equals("/dashboard")) {
            return "dashboard";
        }
        if (path.startsWith("/books")) {
            return "books";
        }
        if (path.startsWith("/members")) {
            return "members";
        }
        if (path.startsWith("/loans/new") || path.equals("/issues/new")) {
            return "issue";
        }
        if (path.startsWith("/loans") || path.startsWith("/issues")) {
            return "history";
        }
        return "";
    }

    @ExceptionHandler(ResourceNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public String handleNotFound(ResourceNotFoundException exception, Model model) {
        model.addAttribute("message", exception.getMessage());
        return "error";
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public String handleBusinessError(IllegalArgumentException exception, HttpServletRequest request,
                                      RedirectAttributes redirectAttributes) {
        redirectAttributes.addFlashAttribute("errorMessage", exception.getMessage());
        return "redirect:" + safePath(request);
    }

    @ExceptionHandler(IllegalStateException.class)
    public String handleStateError(IllegalStateException exception, HttpServletRequest request,
                                   RedirectAttributes redirectAttributes) {
        redirectAttributes.addFlashAttribute("errorMessage", exception.getMessage());
        return "redirect:" + safePath(request);
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    public String handleConstraintError(DataIntegrityViolationException exception, HttpServletRequest request,
                                        RedirectAttributes redirectAttributes) {
        redirectAttributes.addFlashAttribute("errorMessage",
                "That record conflicts with existing data. Check that ISBNs and email addresses are unique.");
        return "redirect:" + safePath(request);
    }

    private String safePath(HttpServletRequest request) {
        String path = request.getRequestURI();
        if (path == null || !path.startsWith("/") || path.startsWith("//")) {
            return "/";
        }
        return path.replaceAll("/\\d+/(delete|return)$", "");
    }
}
