package com.example.librarymanagement.entity;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.math.BigDecimal;
import java.time.LocalDate;
import org.junit.jupiter.api.Test;

class IssueTest {

    @Test
    void loanCanOnlyBeReturnedOnce() {
        Issue issue = new Issue(
                new Book("9780000000001", "A Book", "An Author", "Fiction", 1),
                new Member("Reader", "reader@example.com", null),
                LocalDate.now(),
                LocalDate.now().plusDays(14));

        issue.markReturned(LocalDate.now(), BigDecimal.ZERO);

        assertEquals(IssueStatus.RETURNED, issue.getStatus());
        assertEquals(LocalDate.now(), issue.getReturnDate());
        assertThrows(IllegalStateException.class, () -> issue.markReturned(LocalDate.now(), BigDecimal.ZERO));
    }
}
