package com.example.librarymanagement.service;

import com.example.librarymanagement.dto.BookForm;
import com.example.librarymanagement.entity.Book;
import com.example.librarymanagement.exception.ResourceNotFoundException;
import com.example.librarymanagement.repository.BookRepository;
import com.example.librarymanagement.repository.IssueRepository;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class BookService {

    private final BookRepository bookRepository;
    private final IssueRepository issueRepository;

    public BookService(BookRepository bookRepository, IssueRepository issueRepository) {
        this.bookRepository = bookRepository;
        this.issueRepository = issueRepository;
    }

    @Transactional(readOnly = true)
    public List<Book> search(String query) {
        if (query == null || query.isBlank()) {
            return bookRepository.findAllByOrderByTitleAsc();
        }
        String term = query.trim();
        return bookRepository
                .findByTitleContainingIgnoreCaseOrAuthorContainingIgnoreCaseOrIsbnContainingIgnoreCaseOrCategoryContainingIgnoreCaseOrPublisherContainingIgnoreCaseOrderByTitleAsc(
                        term, term, term, term, term);
    }

    @Transactional(readOnly = true)
    public List<Book> findAll() {
        return search(null);
    }

    @Transactional(readOnly = true)
    public List<Book> findAvailable() {
        return bookRepository.findByAvailableQuantityGreaterThanOrderByTitleAsc(0);
    }

    @Transactional(readOnly = true)
    public Book findById(Long id) {
        return bookRepository.findById(id).orElseThrow(() -> new ResourceNotFoundException("Book not found."));
    }

    @Transactional
    public Book create(BookForm form) {
        String isbn = form.getIsbn().trim();
        ensureUniqueIsbn(isbn, null);
        return bookRepository.save(new Book(isbn, form.getTitle().trim(), form.getAuthor().trim(),
                clean(form.getCategory()), clean(form.getPublisher()), form.getPublicationYear(),
                form.getQuantity()));
    }

    @Transactional
    public Book update(Long id, BookForm form) {
        Book book = findById(id);
        String isbn = form.getIsbn().trim();
        ensureUniqueIsbn(isbn, id);
        book.updateDetails(isbn, form.getTitle().trim(), form.getAuthor().trim(),
                clean(form.getCategory()), clean(form.getPublisher()), form.getPublicationYear(),
                form.getQuantity());
        return bookRepository.save(book);
    }

    @Transactional
    public void delete(Long id) {
        Book book = findById(id);
        if (issueRepository.existsByBookId(id)) {
            throw new IllegalArgumentException("A book with loan history cannot be deleted.");
        }
        bookRepository.delete(book);
    }

    @Transactional(readOnly = true)
    public long totalQuantity() {
        return bookRepository.sumQuantity();
    }

    @Transactional(readOnly = true)
    public long availableQuantity() {
        return bookRepository.sumAvailableQuantity();
    }

    private void ensureUniqueIsbn(String isbn, Long id) {
        boolean exists = id == null
                ? bookRepository.existsByIsbnIgnoreCase(isbn)
                : bookRepository.existsByIsbnIgnoreCaseAndIdNot(isbn, id);
        if (exists) {
            throw new IllegalArgumentException("A book with this ISBN already exists.");
        }
    }

    private String clean(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
