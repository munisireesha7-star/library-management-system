package com.example.librarymanagement.controller;

import com.example.librarymanagement.service.BookService;
import com.example.librarymanagement.service.IssueService;
import com.example.librarymanagement.service.MemberService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class DashboardController {

    private final BookService bookService;
    private final MemberService memberService;
    private final IssueService issueService;

    public DashboardController(BookService bookService, MemberService memberService, IssueService issueService) {
        this.bookService = bookService;
        this.memberService = memberService;
        this.issueService = issueService;
    }

    @GetMapping("/")
    public String dashboard(Model model) {
        model.addAttribute("totalBooks", bookService.totalQuantity());
        model.addAttribute("availableBooks", bookService.availableQuantity());
        model.addAttribute("memberCount", memberService.count());
        model.addAttribute("activeIssueCount", issueService.issuedCount());
        model.addAttribute("overdueCount", issueService.overdueCount());
        model.addAttribute("recentIssues", issueService.findRecent());
        return "dashboard";
    }

    @GetMapping("/dashboard")
    public String dashboardAlias() {
        return "redirect:/";
    }
}
