/*
 * C adaptation of the behavioral cases in GCC's
 * gcc/ordered-hash-map-tests.cc at commit
 * 4bf11aca586c9eef753b6f76d29ae19e1b505694.
 *
 * GCC originals: Copyright (C) 2015-2026 Free Software Foundation, Inc.
 * Modified for JETOS 2026. GPL-3.0-or-later.
 */
#include "ordered_hash_map.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned passes;

#define CHECK(EXPR) do { \
    if (!(EXPR)) { \
        fprintf(stderr, "%s:%d: FAIL: %s\n", __FILE__, __LINE__, #EXPR); \
        exit(1); \
    } \
    ++passes; \
} while (0)

static void
test_map_of_strings_to_int(void)
{
    jetos_omap_str_int m;
    jetos_omap_str_int_init(&m);
    bool existed;

    const char *ostrich = "ostrich";
    const char *elephant = "elephant";
    const char *ant = "ant";
    const char *spider = "spider";
    const char *millipede = "Illacme plenipes";
    const char *eric = "half a bee";

    CHECK(jetos_omap_str_int_elements(&m) == 0);
    CHECK(jetos_omap_str_int_get(&m, ostrich) == NULL);

    CHECK(jetos_omap_str_int_put(&m, ostrich, 2) == false);
    CHECK(jetos_omap_str_int_put(&m, elephant, 4) == false);
    CHECK(jetos_omap_str_int_put(&m, ant, 6) == false);
    existed = true;
    int *value = jetos_omap_str_int_get_or_insert(&m, spider, &existed);
    *value = 8;
    CHECK(existed == false);
    CHECK(jetos_omap_str_int_put(&m, millipede, 750) == false);
    CHECK(jetos_omap_str_int_put(&m, eric, 3) == false);

    CHECK(jetos_omap_str_int_elements(&m) == 6);
    CHECK(*jetos_omap_str_int_get(&m, ostrich) == 2);
    CHECK(*jetos_omap_str_int_get(&m, elephant) == 4);
    CHECK(*jetos_omap_str_int_get(&m, ant) == 6);
    CHECK(*jetos_omap_str_int_get(&m, spider) == 8);
    existed = false;
    CHECK(*jetos_omap_str_int_get_or_insert(&m, millipede, &existed) == 750);
    CHECK(existed == true);
    CHECK(*jetos_omap_str_int_get(&m, eric) == 3);

    const char *keys[] = {ostrich, elephant, ant, spider, millipede, eric};
    const int values[] = {2, 4, 6, 8, 750, 3};
    for (size_t i = 0; i < 6; ++i) {
        const char *key = NULL;
        int stored = 0;
        CHECK(jetos_omap_str_int_nth_active(&m, i, &key, &stored));
        CHECK(key == keys[i]);
        CHECK(stored == values[i]);
    }

    jetos_omap_str_int_destroy(&m);
}

static void
test_map_of_int_to_strings(void)
{
    jetos_omap_int_str m;
    jetos_omap_int_str_init(&m);
    bool existed;

    const char *ostrich = "ostrich";
    const char *elephant = "elephant";
    const char *ant = "ant";
    const char *spider = "spider";
    const char *millipede = "Illacme plenipes";
    const char *eric = "half a bee";

    CHECK(jetos_omap_int_str_elements(&m) == 0);
    CHECK(jetos_omap_int_str_get(&m, 2) == NULL);

    CHECK(jetos_omap_int_str_put(&m, 2, ostrich) == false);
    CHECK(jetos_omap_int_str_put(&m, 4, elephant) == false);
    CHECK(jetos_omap_int_str_put(&m, 6, ant) == false);
    const char **value = jetos_omap_int_str_get_or_insert(&m, 8, &existed);
    *value = spider;
    CHECK(existed == false);
    CHECK(jetos_omap_int_str_put(&m, 750, millipede) == false);
    CHECK(jetos_omap_int_str_put(&m, 3, eric) == false);

    CHECK(jetos_omap_int_str_elements(&m) == 6);
    CHECK(*jetos_omap_int_str_get(&m, 2) == ostrich);
    CHECK(*jetos_omap_int_str_get(&m, 4) == elephant);
    CHECK(*jetos_omap_int_str_get(&m, 6) == ant);
    CHECK(*jetos_omap_int_str_get(&m, 8) == spider);
    CHECK(*jetos_omap_int_str_get_or_insert(&m, 750, &existed) == millipede);
    CHECK(existed == true);
    CHECK(*jetos_omap_int_str_get(&m, 3) == eric);

    const int keys[] = {2, 4, 6, 8, 750, 3};
    const char *values[] = {ostrich, elephant, ant, spider, millipede, eric};
    for (size_t i = 0; i < 6; ++i) {
        int key = 0;
        const char *stored = NULL;
        CHECK(jetos_omap_int_str_nth_active(&m, i, &key, &stored));
        CHECK(key == keys[i]);
        CHECK(stored == values[i]);
    }

    jetos_omap_int_str_destroy(&m);
}

static void
test_growth(void)
{
    enum { count = 20 };
    char strings[count][16];
    jetos_omap_str_int by_string;
    jetos_omap_int_str by_int;
    jetos_omap_str_int_init(&by_string);
    jetos_omap_int_str_init(&by_int);

    for (int i = 0; i < count; ++i) {
        snprintf(strings[i], sizeof(strings[i]), "key-%d", i);
        CHECK(jetos_omap_str_int_put(&by_string, strings[i], i * 3) == false);
        CHECK(jetos_omap_int_str_put(&by_int, i, strings[i]) == false);
    }

    CHECK(jetos_omap_str_int_elements(&by_string) == count);
    CHECK(jetos_omap_int_str_elements(&by_int) == count);
    for (int i = 0; i < count; ++i) {
        CHECK(*jetos_omap_str_int_get(&by_string, strings[i]) == i * 3);
        CHECK(*jetos_omap_int_str_get(&by_int, i) == strings[i]);
    }

    jetos_omap_int_str_destroy(&by_int);
    jetos_omap_str_int_destroy(&by_string);
}

static void
test_removal(void)
{
    jetos_omap_str_int m;
    jetos_omap_str_int_init(&m);
    const char *ostrich = "ostrich";

    CHECK(jetos_omap_str_int_put(&m, ostrich, 2) == false);
    CHECK(jetos_omap_str_int_elements(&m) == 1);
    CHECK(*jetos_omap_str_int_get(&m, ostrich) == 2);

    const char *key = NULL;
    int value = 0;
    CHECK(jetos_omap_str_int_nth_active(&m, 0, &key, &value));
    CHECK(key == ostrich);
    CHECK(value == 2);

    jetos_omap_str_int_remove(&m, ostrich);
    CHECK(jetos_omap_str_int_elements(&m) == 0);
    CHECK(!jetos_omap_str_int_nth_active(&m, 0, &key, &value));

    CHECK(jetos_omap_str_int_put(&m, ostrich, 42) == false);
    CHECK(jetos_omap_str_int_elements(&m) == 1);
    CHECK(*jetos_omap_str_int_get(&m, ostrich) == 42);
    CHECK(jetos_omap_str_int_nth_active(&m, 0, &key, &value));
    CHECK(key == ostrich);
    CHECK(value == 42);

    jetos_omap_str_int_destroy(&m);
}

static void
test_copy_ctor_behavior(void)
{
    jetos_omap_str_int m;
    jetos_omap_str_int copy;
    jetos_omap_str_int_init(&m);
    jetos_omap_str_int_init(&copy);
    const char *ostrich = "ostrich";

    CHECK(jetos_omap_str_int_put(&m, ostrich, 2) == false);
    CHECK(jetos_omap_str_int_elements(&m) == 1);
    CHECK(*jetos_omap_str_int_get(&m, ostrich) == 2);

    CHECK(jetos_omap_str_int_copy(&copy, &m));
    CHECK(jetos_omap_str_int_elements(&copy) == 1);
    CHECK(*jetos_omap_str_int_get(&copy, ostrich) == 2);

    jetos_omap_str_int_remove(&m, ostrich);
    CHECK(jetos_omap_str_int_elements(&m) == 0);
    CHECK(jetos_omap_str_int_elements(&copy) == 1);
    CHECK(*jetos_omap_str_int_get(&copy, ostrich) == 2);

    jetos_omap_str_int_destroy(&copy);
    jetos_omap_str_int_destroy(&m);
}

int
main(void)
{
    test_map_of_strings_to_int();
    test_map_of_int_to_strings();
    test_growth();
    test_removal();
    test_copy_ctor_behavior();
    printf("ordered_hash_map C port: %u checks passed\n", passes);
    return 0;
}
