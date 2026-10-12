package com.example.librarymanagement.repository;

import com.example.librarymanagement.entity.Issue;
import com.example.librarymanagement.entity.IssueStatus;
import java.util.List;
import java.util.Optional;
import java.time.LocalDate;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface IssueRepository extends JpaRepository<Issue, Long> {

    @EntityGraph(attributePaths = {"book", "member"})
    List<Issue> findTop5ByOrderByIssueDateDescIdDesc();

    @EntityGraph(attributePaths = {"book", "member"})
    List<Issue> findAllByOrderByIssueDateDescIdDesc();

    @EntityGraph(attributePaths = {"book", "member"})
    List<Issue> findByStatusOrderByDueDateAsc(IssueStatus status);

    @EntityGraph(attributePaths = {"book", "member"})
    List<Issue> findByStatusAndDueDateBeforeOrderByDueDateAsc(IssueStatus status, LocalDate dueDate);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select issue from Issue issue where issue.id = :id")
    Optional<Issue> findByIdForUpdate(@Param("id") Long id);

    long countByStatus(IssueStatus status);
    long countByStatusAndDueDateBefore(IssueStatus status, LocalDate dueDate);
    boolean existsByBookId(Long bookId);
    boolean existsByMemberId(Long memberId);
}
