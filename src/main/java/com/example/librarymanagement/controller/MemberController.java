package com.example.librarymanagement.controller;

import com.example.librarymanagement.dto.MemberForm;
import com.example.librarymanagement.entity.Member;
import com.example.librarymanagement.service.MemberService;
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
@RequestMapping("/members")
public class MemberController {

    private final MemberService memberService;

    public MemberController(MemberService memberService) {
        this.memberService = memberService;
    }

    @GetMapping
    public String list(@RequestParam(required = false) String q, Model model) {
        model.addAttribute("members", memberService.search(q));
        model.addAttribute("q", q);
        return "members";
    }

    @GetMapping("/new")
    public String createForm(Model model) {
        model.addAttribute("memberForm", new MemberForm());
        return "add-member";
    }

    @PostMapping
    public String create(@Valid @ModelAttribute("memberForm") MemberForm form, BindingResult result,
                         Model model, RedirectAttributes redirectAttributes) {
        if (result.hasErrors()) {
            return "add-member";
        }
        try {
            memberService.create(form);
        } catch (IllegalArgumentException exception) {
            result.reject("member.invalid", exception.getMessage());
            return "add-member";
        }
        redirectAttributes.addFlashAttribute("successMessage", "Member registered.");
        return "redirect:/members";
    }

    @GetMapping("/{id}/edit")
    public String editForm(@PathVariable Long id, Model model) {
        Member member = memberService.findById(id);
        MemberForm form = new MemberForm();
        form.setName(member.getName());
        form.setEmail(member.getEmail());
        form.setPhone(member.getPhone());
        form.setDepartment(member.getDepartment());
        model.addAttribute("memberForm", form);
        model.addAttribute("memberId", id);
        return "edit-member";
    }

    @PostMapping("/{id}/edit")
    public String edit(@PathVariable Long id, @Valid @ModelAttribute("memberForm") MemberForm form,
                       BindingResult result, Model model, RedirectAttributes redirectAttributes) {
        if (result.hasErrors()) {
            model.addAttribute("memberId", id);
            return "edit-member";
        }
        try {
            memberService.update(id, form);
        } catch (IllegalArgumentException exception) {
            result.reject("member.invalid", exception.getMessage());
            model.addAttribute("memberId", id);
            return "edit-member";
        }
        redirectAttributes.addFlashAttribute("successMessage", "Member details updated.");
        return "redirect:/members";
    }

    @PostMapping("/{id}/delete")
    public String delete(@PathVariable Long id, RedirectAttributes redirectAttributes) {
        memberService.delete(id);
        redirectAttributes.addFlashAttribute("successMessage", "Member removed.");
        return "redirect:/members";
    }
}
