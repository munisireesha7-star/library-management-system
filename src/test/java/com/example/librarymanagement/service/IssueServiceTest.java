package com.example.librarymanagement.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.example.librarymanagement.entity.Book;
import com.example.librarymanagement.entity.Issue;
import com.example.librarymanagement.entity.Member;
import com.example.librarymanagement.repository.BookRepository;
import com.example.librarymanagement.repository.IssueRepository;
import com.example.librarymanagement.repository.MemberRepository;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

class IssueServiceTest {

    @Test
    void returningLateBookCalculatesFiveRupeesPerLateDayAndRestoresAvailability() {
        IssueRepository issueRepository = mock(IssueRepository.class);
        BookRepository bookRepository = mock(BookRepository.class);
        MemberRepository memberRepository = mock(MemberRepository.class);
        IssueService service = new IssueService(issueRepository, bookRepository, memberRepository);

        LocalDate today = LocalDate.now();
        Book book = new Book("9780000000001", "A Book", "An Author", "Fiction", 1);
        ReflectionTestUtils.setField(book, "id", 1L);
        book.checkOut();
        Issue issue = new Issue(book, new Member("Reader", "reader@example.com", null),
                today.minusDays(20), today.minusDays(10));
        when(issueRepository.findByIdForUpdate(1L)).thenReturn(Optional.of(issue));
        when(bookRepository.findByIdForUpdate(1L)).thenReturn(Optional.of(book));

        service.returnBook(1L);

        assertEquals(BigDecimal.valueOf(50), issue.getFine());
        assertEquals(today, issue.getReturnDate());
        assertEquals(1, book.getAvailableQuantity());
        verify(issueRepository).save(issue);
    }

    @Test
    void returningOnTimeDoesNotCreateAFine() {
        IssueRepository issueRepository = mock(IssueRepository.class);
        BookRepository bookRepository = mock(BookRepository.class);
        MemberRepository memberRepository = mock(MemberRepository.class);
        IssueService service = new IssueService(issueRepository, bookRepository, memberRepository);

        LocalDate today = LocalDate.now();
        Book book = new Book("9780000000002", "Another Book", "An Author", "Fiction", 1);
        ReflectionTestUtils.setField(book, "id", 1L);
        book.checkOut();
        Issue issue = new Issue(book, new Member("Reader", "reader@example.com", null),
                today.minusDays(2), today);
        when(issueRepository.findByIdForUpdate(1L)).thenReturn(Optional.of(issue));
        when(bookRepository.findByIdForUpdate(1L)).thenReturn(Optional.of(book));

        service.returnBook(1L);

        assertEquals(BigDecimal.ZERO, issue.getFine());
        assertEquals(1, book.getAvailableQuantity());
    }
}
