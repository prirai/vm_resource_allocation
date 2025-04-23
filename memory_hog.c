#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <signal.h>

#define MIN_MB 100
#define MAX_MB 2000
#define DEALLOC_CHUNK_MB 100
#define MB_IN_BYTES (1024UL * 1024UL)
#define DEALLOC_CHUNK_BYTES (DEALLOC_CHUNK_MB * MB_IN_BYTES)

static char *buffer = NULL;
static size_t current_allocated_size = 0;

/**
 * Handles signals for graceful cleanup of allocated memory.
 * Frees any remaining memory and exits the program.
 *
 * @param sig The signal number received.
 */
void handle_signal(int sig) {
    printf("\nCaught signal %d. Cleaning up remaining memory...\n", sig);
    if (buffer != NULL) {
        printf("Freeing remaining %zu bytes (%lu MB).\n", current_allocated_size, current_allocated_size / MB_IN_BYTES);
        fflush(stdout);
        free(buffer);
        buffer = NULL;
        current_allocated_size = 0;
    }
    printf("Exiting due to signal.\n");
    fflush(stdout);
    exit(0);
}

/**
 * Main function to allocate a random amount of memory, fill it with random data,
 * and gradually deallocate it in chunks. Handles signals for cleanup during the process.
 *
 * @return Exit status code.
 */
int main() {
    size_t min_bytes = MIN_MB * MB_IN_BYTES;
    size_t max_bytes = MAX_MB * MB_IN_BYTES;
    size_t range = max_bytes - min_bytes;
    size_t random_offset;
    size_t initial_target_size_bytes;
    size_t initial_target_size_mb;

    srand(time(NULL));

    if (range == 0) {
        random_offset = 0;
    } else {
        random_offset = (size_t)rand() % (range + 1);
    }
    initial_target_size_bytes = min_bytes + random_offset;
    initial_target_size_mb = initial_target_size_bytes / MB_IN_BYTES;

    printf("Attempting to allocate initial %zu MB (%zu bytes).\n", initial_target_size_mb, initial_target_size_bytes);
    fflush(stdout);

    buffer = (char *)malloc(initial_target_size_bytes);
    if (buffer == NULL) {
        perror("Initial memory allocation failed");
        fprintf(stderr, "Could not allocate %zu MB.\n", initial_target_size_mb);
        return 1;
    }
    current_allocated_size = initial_target_size_bytes;

    printf("Successfully allocated %zu MB.\n", initial_target_size_mb);
    printf("Filling memory with random data...\n");
    fflush(stdout);

    for (size_t i = 0; i < current_allocated_size; ++i) {
        buffer[i] = rand() % 256;
    }

    printf("Finished filling memory. Current allocation: %zu MB.\n", current_allocated_size / MB_IN_BYTES);
    printf("Starting gradual deallocation (%d MB chunks per second)...\n", DEALLOC_CHUNK_MB);
    fflush(stdout);

    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    while (current_allocated_size > 0) {
        sleep(1);

        size_t size_to_remove = DEALLOC_CHUNK_BYTES;
        if (current_allocated_size < size_to_remove) {
            size_to_remove = current_allocated_size;
        }

        size_t new_size = current_allocated_size - size_to_remove;

        printf("Deallocating ~%d MB. New target size: %zu MB\n", DEALLOC_CHUNK_MB, new_size / MB_IN_BYTES);
        fflush(stdout);

        char *temp_buffer = (char*)realloc(buffer, new_size);

        if (new_size > 0 && temp_buffer == NULL) {
            perror("realloc failed when shrinking");
            fprintf(stderr, "Error shrinking buffer. Freeing remaining and exiting.\n");
            free(buffer);
            return 1;
        }

        buffer = temp_buffer;
        current_allocated_size = new_size;

        if (current_allocated_size == 0) {
             printf("Buffer fully deallocated.\n");
             fflush(stdout);
             buffer = NULL;
             break;
        }
    }

    printf("All memory deallocated. Exiting normally.\n");
    fflush(stdout);

    return 0;
}
