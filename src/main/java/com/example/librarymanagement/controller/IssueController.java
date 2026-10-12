package com.example.librarymanagement.controller;

import com.example.librarymanagement.dto.IssueForm;
import com.example.librarymanagement.entity.Issue;
import com.example.librarymanagement.service.BookService;
import com.example.librarymanagement.service.IssueService;
import com.example.librarymanagement.service.MemberService;
import jakarta.validation.Valid;
import java.time.LocalDate;
import java.util.List;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.validation.BindingResult;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;

@Controller
@RequestMapping({"/loans", "/issues"})
public class IssueController {

    private final IssueService issueService;
    private final BookService bookService;
    private final MemberService memberService;

    public IssueController(IssueService issueService, BookService bookService, MemberService memberService) {
        this.issueService = issueService;
        this.bookService = bookService;
        this.memberService = memberService;
    }

    @GetMapping({"", "/history"})
    public String list(Model model) {
        populateModel(model, issueService.findAll(), "history");
        return "issue-history";
    }

    @GetMapping({"/current", "/issued"})
    public String current(Model model) {
        populateModel(model, issueService.findCurrentlyIssued(), "current");
        return "issue-history";
    }

    @GetMapping("/overdue")
    public String overdue(Model model) {
        populateModel(model, issueService.findOverdue(), "overdue");
        return "issue-history";
    }

    @GetMapping("/new")
    public String issueForm(Model model) {
        populateIssueForm(model, new IssueForm());
        return "issue-book";
    }

    @PostMapping({"", "/issue"})
    public String issue(@Valid @ModelAttribute("issueForm") IssueForm form, BindingResult result, Model model,
                         RedirectAttributes redirectAttributes) {
        if (result.hasErrors()) {
            populateIssueForm(model, form);
            return "issue-book";
        }
        try {
            issueService.issueBook(form);
        } catch (IllegalArgumentException exception) {
            result.reject("issue.invalid", exception.getMessage());
            populateIssueForm(model, form);
            return "issue-book";
        }
        redirectAttributes.addFlashAttribute("successMessage", "Book checked out successfully.");
        return "redirect:/loans/history";
    }

    @PostMapping("/{id}/return")
    public String returnBook(@PathVariable Long id, RedirectAttributes redirectAttributes) {
        Issue issue = issueService.returnBook(id);
        redirectAttributes.addFlashAttribute("successMessage",
                "Book returned successfully. Fine: ₹" + issue.getFine().toPlainString());
        return "redirect:/loans/history";
    }

    private void populateModel(Model model, List<Issue> issues, String issueView) {
        model.addAttribute("issues", issues);
        model.addAttribute("issueView", issueView);
        model.addAttribute("today", LocalDate.now());
    }

    private void populateIssueForm(Model model, IssueForm form) {
        model.addAttribute("issueForm", form);
        model.addAttribute("books", bookService.findAvailable());
        model.addAttribute("members", memberService.findAll());
    }
}
