package com.example.librarymanagement.repository;

import com.example.librarymanagement.entity.Book;
import java.util.List;
import java.util.Optional;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface BookRepository extends JpaRepository<Book, Long> {
    @Query("select coalesce(sum(book.quantity), 0) from Book book")
    long sumQuantity();

    @Query("select coalesce(sum(book.availableQuantity), 0) from Book book")
    long sumAvailableQuantity();

    List<Book> findAllByOrderByTitleAsc();
    List<Book> findByAvailableQuantityGreaterThanOrderByTitleAsc(int availableQuantity);
    boolean existsByIsbnIgnoreCase(String isbn);
    boolean existsByIsbnIgnoreCaseAndIdNot(String isbn, Long id);
    List<Book> findByTitleContainingIgnoreCaseOrAuthorContainingIgnoreCaseOrIsbnContainingIgnoreCaseOrCategoryContainingIgnoreCaseOrPublisherContainingIgnoreCaseOrderByTitleAsc(
            String title, String author, String isbn, String category, String publisher);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select book from Book book where book.id = :id")
    Optional<Book> findByIdForUpdate(@Param("id") Long id);
}
