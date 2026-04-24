package com.metromargeo.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;

import static org.springframework.security.config.Customizer.withDefaults;

/**
 * [O GUARDA-COSTAS DA API]: Esta classe define quem pode entrar e quem fica de fora.
 * Para a GFT, é essencial mostrar que você sabe configurar a 'SecurityFilterChain'.
 */
@Configuration
@EnableWebSecurity // Ativa a segurança web no projeto
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .headers(headers -> headers.frameOptions(frame -> frame.disable()))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/h2-console/**").permitAll()
                .requestMatchers("/api/imoveis/**").permitAll()
                .anyRequest().authenticated()
            )
            .formLogin(withDefaults())
            .httpBasic(withDefaults());

        return http.build();
    }

    /**
     * [O COFRE DOS USUÁRIOS]: Aqui definimos quem pode logar na API.
     * Na GFT, diga que você está usando 'InMemory' para testes, mas que 
     * em produção usaria um Banco de Dados ou OAuth2.
     */
    @Bean
    public org.springframework.security.core.userdetails.UserDetailsService userDetailsService() {
        org.springframework.security.core.userdetails.UserDetails user =
            org.springframework.security.core.userdetails.User.withDefaultPasswordEncoder()
                .username("admin")
                .password("gft2026")
                .roles("ADMIN")
                .build();

        return new org.springframework.security.provisioning.InMemoryUserDetailsManager(user);
    }
}
