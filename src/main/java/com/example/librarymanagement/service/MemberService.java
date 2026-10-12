package com.example.librarymanagement.service;

import com.example.librarymanagement.dto.MemberForm;
import com.example.librarymanagement.entity.Member;
import com.example.librarymanagement.exception.ResourceNotFoundException;
import com.example.librarymanagement.repository.IssueRepository;
import com.example.librarymanagement.repository.MemberRepository;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class MemberService {

    private final MemberRepository memberRepository;
    private final IssueRepository issueRepository;

    public MemberService(MemberRepository memberRepository, IssueRepository issueRepository) {
        this.memberRepository = memberRepository;
        this.issueRepository = issueRepository;
    }

    @Transactional(readOnly = true)
    public List<Member> findAll() {
        return memberRepository.findAllByOrderByNameAsc();
    }

    @Transactional(readOnly = true)
    public List<Member> search(String query) {
        if (query == null || query.isBlank()) {
            return findAll();
        }
        String term = query.trim();
        return memberRepository
                .findByNameContainingIgnoreCaseOrEmailContainingIgnoreCaseOrPhoneContainingIgnoreCaseOrDepartmentContainingIgnoreCaseOrderByNameAsc(
                        term, term, term, term);
    }

    @Transactional(readOnly = true)
    public Member findById(Long id) {
        return memberRepository.findById(id).orElseThrow(() -> new ResourceNotFoundException("Member not found."));
    }

    @Transactional
    public Member create(MemberForm form) {
        String email = form.getEmail().trim();
        ensureUniqueEmail(email, null);
        return memberRepository.save(new Member(form.getName().trim(), email, clean(form.getPhone()),
                clean(form.getDepartment())));
    }

    @Transactional
    public Member update(Long id, MemberForm form) {
        Member member = findById(id);
        String email = form.getEmail().trim();
        ensureUniqueEmail(email, id);
        member.updateDetails(form.getName().trim(), email, clean(form.getPhone()), clean(form.getDepartment()));
        return memberRepository.save(member);
    }

    @Transactional
    public void delete(Long id) {
        Member member = findById(id);
        if (issueRepository.existsByMemberId(id)) {
            throw new IllegalArgumentException("A member with loan history cannot be deleted.");
        }
        memberRepository.delete(member);
    }

    @Transactional(readOnly = true)
    public long count() {
        return memberRepository.count();
    }

    private void ensureUniqueEmail(String email, Long id) {
        boolean exists = id == null
                ? memberRepository.existsByEmailIgnoreCase(email)
                : memberRepository.existsByEmailIgnoreCaseAndIdNot(email, id);
        if (exists) {
            throw new IllegalArgumentException("A member with this email address already exists.");
        }
    }

    private String clean(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
