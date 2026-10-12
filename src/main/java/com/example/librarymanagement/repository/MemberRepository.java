package com.example.librarymanagement.repository;

import com.example.librarymanagement.entity.Member;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MemberRepository extends JpaRepository<Member, Long> {
    boolean existsByEmailIgnoreCase(String email);
    boolean existsByEmailIgnoreCaseAndIdNot(String email, Long id);
    List<Member> findAllByOrderByNameAsc();
    List<Member> findByNameContainingIgnoreCaseOrEmailContainingIgnoreCaseOrPhoneContainingIgnoreCaseOrDepartmentContainingIgnoreCaseOrderByNameAsc(
            String name, String email, String phone, String department);
}
