package com.example.librarymanagement.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.FutureOrPresent;
import java.time.LocalDate;

public class IssueForm {

    @NotNull
    private Long bookId;

    @NotNull
    private Long memberId;

    @NotNull
    @FutureOrPresent
    private LocalDate dueOn = LocalDate.now().plusDays(14);

    public Long getBookId() { return bookId; }
    public void setBookId(Long bookId) { this.bookId = bookId; }
    public Long getMemberId() { return memberId; }
    public void setMemberId(Long memberId) { this.memberId = memberId; }
    public LocalDate getDueOn() { return dueOn; }
    public void setDueOn(LocalDate dueOn) { this.dueOn = dueOn; }
}
