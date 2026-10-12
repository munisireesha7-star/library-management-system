package com.example.librarymanagement.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "books")
public class Book {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank
    @Size(max = 20)
    @Column(nullable = false, unique = true, length = 20)
    private String isbn;

    @NotBlank
    @Size(max = 150)
    @Column(nullable = false, length = 150)
    private String title;

    @NotBlank
    @Size(max = 120)
    @Column(nullable = false, length = 120)
    private String author;

    @Size(max = 80)
    @Column(length = 80)
    private String category;

    @Size(max = 150)
    @Column(length = 150)
    private String publisher;

    @Min(0)
    @Max(9999)
    private Integer publicationYear;

    @Min(0)
    @Column(nullable = false)
    private int quantity;

    @Min(0)
    @Column(nullable = false)
    private int availableQuantity;

    @OneToMany(mappedBy = "book")
    private List<Issue> issues = new ArrayList<>();

    protected Book() {
    }

    public Book(String isbn, String title, String author, String category, int quantity) {
        this(isbn, title, author, category, null, null, quantity);
    }

    public Book(String isbn, String title, String author, String category,
                String publisher, Integer publicationYear, int quantity) {
        this.isbn = isbn;
        this.title = title;
        this.author = author;
        this.category = category;
        this.publisher = publisher;
        this.publicationYear = publicationYear;
        this.quantity = quantity;
        this.availableQuantity = quantity;
    }

    public void updateDetails(String isbn, String title, String author, String category,
                              String publisher, Integer publicationYear, int quantity) {
        int checkedOutCopies = this.quantity - this.availableQuantity;
        if (quantity < checkedOutCopies) {
            throw new IllegalArgumentException("Total copies cannot be less than the number currently checked out.");
        }
        this.isbn = isbn;
        this.title = title;
        this.author = author;
        this.category = category;
        this.publisher = publisher;
        this.publicationYear = publicationYear;
        this.quantity = quantity;
        this.availableQuantity = quantity - checkedOutCopies;
    }

    public void checkOut() {
        if (availableQuantity < 1) {
            throw new IllegalArgumentException("No copies of this book are currently available.");
        }
        availableQuantity--;
    }

    public void checkIn() {
        if (availableQuantity >= quantity) {
            throw new IllegalStateException("All copies of this book are already in the library.");
        }
        availableQuantity++;
    }

    public Long getId() { return id; }
    public String getIsbn() { return isbn; }
    public String getTitle() { return title; }
    public String getAuthor() { return author; }
    public String getCategory() { return category; }
    public String getPublisher() { return publisher; }
    public Integer getPublicationYear() { return publicationYear; }
    public int getQuantity() { return quantity; }
    public int getAvailableQuantity() { return availableQuantity; }
    public List<Issue> getIssues() { return issues; }

    void addIssue(Issue issue) {
        issues.add(issue);
    }
}
