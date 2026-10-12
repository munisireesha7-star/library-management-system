package com.example.librarymanagement.entity;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

class BookTest {

    @Test
    void checkoutAndReturnKeepInventoryBalanced() {
        Book book = new Book("9780000000001", "A Book", "An Author", "Fiction", 3);

        book.checkOut();
        book.checkOut();
        assertEquals(1, book.getAvailableQuantity());

        book.checkIn();
        assertEquals(2, book.getAvailableQuantity());
    }

    @Test
    void cannotCheckoutWhenNoCopiesAreAvailable() {
        Book book = new Book("9780000000001", "A Book", "An Author", "Fiction", 1);
        book.checkOut();

        assertThrows(IllegalArgumentException.class, book::checkOut);
        assertEquals(0, book.getAvailableQuantity());
    }

    @Test
    void editingTotalCopiesPreservesCheckedOutCopies() {
        Book book = new Book("9780000000001", "A Book", "An Author", "Fiction", 4);
        book.checkOut();

        book.updateDetails("9780000000001", "A Book", "An Author", "Fiction",
                null, null, 5);

        assertEquals(5, book.getQuantity());
        assertEquals(4, book.getAvailableQuantity());
    }

    @Test
    void cannotReduceCopiesBelowCheckedOutCount() {
        Book book = new Book("9780000000001", "A Book", "An Author", "Fiction", 2);
        book.checkOut();
        book.checkOut();

        assertThrows(IllegalArgumentException.class,
                () -> book.updateDetails("9780000000001", "A Book", "An Author", "Fiction",
                        null, null, 1));
        assertEquals(0, book.getAvailableQuantity());
    }
}
