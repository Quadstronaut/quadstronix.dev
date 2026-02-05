# Stage 1: Build Caddy with the Porkbun DNS plugin
FROM caddy:builder AS builder

RUN xcaddy build \
    --with github.com/caddy-dns/porkbun

# Stage 2: Create the final image
FROM caddy:latest

# Copy the custom binary from the builder stage
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
