package com.example.librarymanagement.controller;

import com.example.librarymanagement.dto.BookForm;
import com.example.librarymanagement.entity.Book;
import com.example.librarymanagement.service.BookService;
import jakarta.validation.Valid;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.validation.BindingResult;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;

@Controller
@RequestMapping("/books")
public class BookController {

    private final BookService bookService;

    public BookController(BookService bookService) {
        this.bookService = bookService;
    }

    @GetMapping
    public String list(@RequestParam(required = false) String q, Model model) {
        model.addAttribute("books", bookService.search(q));
        model.addAttribute("q", q);
        return "books";
    }

    @GetMapping("/new")
    public String createForm(Model model) {
        model.addAttribute("bookForm", new BookForm());
        return "add-book";
    }

    @PostMapping
    public String create(@Valid @ModelAttribute("bookForm") BookForm form, BindingResult result, Model model,
                         RedirectAttributes redirectAttributes) {
        if (result.hasErrors()) {
            return "add-book";
        }
        try {
            bookService.create(form);
        } catch (IllegalArgumentException exception) {
            result.reject("book.invalid", exception.getMessage());
            return "add-book";
        }
        redirectAttributes.addFlashAttribute("successMessage", "Book added to the catalog.");
        return "redirect:/books";
    }

    @GetMapping("/{id}/edit")
    public String editForm(@PathVariable Long id, Model model) {
        Book book = bookService.findById(id);
        BookForm form = new BookForm();
        form.setIsbn(book.getIsbn());
        form.setTitle(book.getTitle());
        form.setAuthor(book.getAuthor());
        form.setCategory(book.getCategory());
        form.setPublisher(book.getPublisher());
        form.setPublicationYear(book.getPublicationYear());
        form.setQuantity(book.getQuantity());
        model.addAttribute("bookForm", form);
        model.addAttribute("bookId", id);
        return "edit-book";
    }

    @PostMapping("/{id}/edit")
    public String edit(@PathVariable Long id, @Valid @ModelAttribute("bookForm") BookForm form,
                       BindingResult result, Model model, RedirectAttributes redirectAttributes) {
        if (result.hasErrors()) {
            model.addAttribute("bookId", id);
            return "edit-book";
        }
        try {
            bookService.update(id, form);
        } catch (IllegalArgumentException exception) {
            result.reject("book.invalid", exception.getMessage());
            model.addAttribute("bookId", id);
            return "edit-book";
        }
        redirectAttributes.addFlashAttribute("successMessage", "Book details updated.");
        return "redirect:/books";
    }

    @PostMapping("/{id}/delete")
    public String delete(@PathVariable Long id, RedirectAttributes redirectAttributes) {
        bookService.delete(id);
        redirectAttributes.addFlashAttribute("successMessage", "Book removed from the catalog.");
        return "redirect:/books";
    }
}
