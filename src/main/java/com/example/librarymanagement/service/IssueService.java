package com.example.librarymanagement.service;

import com.example.librarymanagement.dto.IssueForm;
import com.example.librarymanagement.entity.Book;
import com.example.librarymanagement.entity.Issue;
import com.example.librarymanagement.entity.IssueStatus;
import com.example.librarymanagement.entity.Member;
import com.example.librarymanagement.exception.ResourceNotFoundException;
import com.example.librarymanagement.repository.BookRepository;
import com.example.librarymanagement.repository.IssueRepository;
import com.example.librarymanagement.repository.MemberRepository;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class IssueService {

    private final IssueRepository issueRepository;
    private final BookRepository bookRepository;
    private final MemberRepository memberRepository;

    public IssueService(IssueRepository issueRepository, BookRepository bookRepository,
                       MemberRepository memberRepository) {
        this.issueRepository = issueRepository;
        this.bookRepository = bookRepository;
        this.memberRepository = memberRepository;
    }

    @Transactional(readOnly = true)
    public List<Issue> findAll() {
        return issueRepository.findAllByOrderByIssueDateDescIdDesc();
    }

    @Transactional(readOnly = true)
    public List<Issue> findRecent() {
        return issueRepository.findTop5ByOrderByIssueDateDescIdDesc();
    }

    @Transactional(readOnly = true)
    public List<Issue> findCurrentlyIssued() {
        return issueRepository.findByStatusOrderByDueDateAsc(IssueStatus.ISSUED);
    }

    @Transactional(readOnly = true)
    public List<Issue> findOverdue() {
        return issueRepository.findByStatusAndDueDateBeforeOrderByDueDateAsc(IssueStatus.ISSUED, LocalDate.now());
    }

    @Transactional
    public Issue issueBook(IssueForm form) {
        if (form.getBookId() == null) {
            throw new IllegalArgumentException("Select a book to issue.");
        }
        if (form.getMemberId() == null) {
            throw new IllegalArgumentException("Select a member for this issue.");
        }
        if (form.getDueOn() == null) {
            throw new IllegalArgumentException("A due date is required.");
        }
        LocalDate issueDate = LocalDate.now();
        if (form.getDueOn().isBefore(issueDate)) {
            throw new IllegalArgumentException("The due date must be today or later.");
        }
        Book book = bookRepository.findByIdForUpdate(form.getBookId())
                .orElseThrow(() -> new ResourceNotFoundException("Selected book was not found."));
        Member member = memberRepository.findById(form.getMemberId())
                .orElseThrow(() -> new ResourceNotFoundException("Selected member was not found."));
        book.checkOut();
        return issueRepository.save(new Issue(book, member, issueDate, form.getDueOn()));
    }

    @Transactional
    public Issue returnBook(Long issueId) {
        Issue issue = issueRepository.findByIdForUpdate(issueId)
                .orElseThrow(() -> new ResourceNotFoundException("Issue not found."));
        LocalDate returnDate = LocalDate.now();
        BigDecimal fine = calculateFine(issue.getDueDate(), returnDate);
        issue.markReturned(returnDate, fine);
        Book book = bookRepository.findByIdForUpdate(issue.getBook().getId())
                .orElseThrow(() -> new ResourceNotFoundException("The book for this issue no longer exists."));
        book.checkIn();
        return issueRepository.save(issue);
    }

    static BigDecimal calculateFine(LocalDate dueDate, LocalDate returnDate) {
        // The due date itself is not late; charge only for complete days after it.
        long lateDays = Math.max(0, ChronoUnit.DAYS.between(dueDate, returnDate));
        return BigDecimal.valueOf(lateDays).multiply(BigDecimal.valueOf(5));
    }

    @Transactional(readOnly = true)
    public long issuedCount() {
        return issueRepository.countByStatus(IssueStatus.ISSUED);
    }

    @Transactional(readOnly = true)
    public long overdueCount() {
        return issueRepository.countByStatusAndDueDateBefore(IssueStatus.ISSUED, LocalDate.now());
    }
}
