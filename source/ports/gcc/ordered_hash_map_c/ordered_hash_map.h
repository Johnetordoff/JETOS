/*
 * JETOS C port experiment for GCC ordered_hash_map behavior.
 *
 * Based on concepts and test behavior from GCC:
 *   gcc/ordered-hash-map.h
 *   gcc/ordered-hash-map-tests.cc
 * pinned at GCC commit 4bf11aca586c9eef753b6f76d29ae19e1b505694.
 *
 * GCC originals: Copyright (C) Free Software Foundation, Inc.
 * JETOS C translation: modified 2026.
 *
 * This derivative experiment is distributed under GPL-3.0-or-later.
 */
#ifndef JETOS_GCC_ORDERED_HASH_MAP_C_H
#define JETOS_GCC_ORDERED_HASH_MAP_C_H

#include <stdbool.h>
#include <stddef.h>

/* Explicit specialization corresponding to ordered_hash_map<const char *, int>.
   Keys are borrowed and compared by pointer identity, matching GCC pointer-key
   semantics for this experiment. */

typedef struct {
    const char *key;
    int value;
    bool active;
} jetos_omap_str_int_entry;

typedef struct {
    jetos_omap_str_int_entry *entries;
    size_t length;      /* all keys ever inserted */
    size_t capacity;
    size_t active_count;
} jetos_omap_str_int;

void jetos_omap_str_int_init(jetos_omap_str_int *map);
void jetos_omap_str_int_destroy(jetos_omap_str_int *map);
bool jetos_omap_str_int_copy(jetos_omap_str_int *dst, const jetos_omap_str_int *src);
bool jetos_omap_str_int_put(jetos_omap_str_int *map, const char *key, int value);
int *jetos_omap_str_int_get(jetos_omap_str_int *map, const char *key);
int *jetos_omap_str_int_get_or_insert(jetos_omap_str_int *map, const char *key,
                                    bool *existed);
void jetos_omap_str_int_remove(jetos_omap_str_int *map, const char *key);
size_t jetos_omap_str_int_elements(const jetos_omap_str_int *map);
bool jetos_omap_str_int_nth_active(const jetos_omap_str_int *map, size_t n,
                                 const char **key, int *value);

/* Explicit specialization corresponding to ordered_hash_map<int_hash<...>,
   const char *>. Values are borrowed strings. */

typedef struct {
    int key;
    const char *value;
    bool active;
} jetos_omap_int_str_entry;

typedef struct {
    jetos_omap_int_str_entry *entries;
    size_t length;
    size_t capacity;
    size_t active_count;
} jetos_omap_int_str;

void jetos_omap_int_str_init(jetos_omap_int_str *map);
void jetos_omap_int_str_destroy(jetos_omap_int_str *map);
bool jetos_omap_int_str_put(jetos_omap_int_str *map, int key, const char *value);
const char **jetos_omap_int_str_get(jetos_omap_int_str *map, int key);
const char **jetos_omap_int_str_get_or_insert(jetos_omap_int_str *map, int key,
                                            bool *existed);
size_t jetos_omap_int_str_elements(const jetos_omap_int_str *map);
bool jetos_omap_int_str_nth_active(const jetos_omap_int_str *map, size_t n,
                                 int *key, const char **value);

#endif
